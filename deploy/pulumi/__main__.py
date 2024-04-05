"""An AWS Python Pulumi plan."""

import base64
import hashlib
import json

import pinecone_pulumi as pinecone
import pulumi
import pulumi_aws as aws
import pulumi_docker as docker
from lib import base

#
# Config
#

config = pulumi.Config()
app_name = config.require("appName")
app_config_file = config.require("appConfigFile")
data_load_event_rule_schedule = config.require("dataLoadEventRuleSchedule")
data_load_event_rule_state = config.require("dataLoadEventRuleState")
lambda_execution_timeout = config.require_int("lambdaExecutionTimeout")
log_level = config.require("logLevel")
openai_api_key_secret_name = config.require("openAiApiKeySecretName")
pinecone_api_key_secret_name = config.require("pineconeApiKeySecretName")
slack_bot_token_secret_name = config.require("slackBotTokenSecretName")

aws_caller_identity = aws.get_caller_identity()
account_id = aws_caller_identity.account_id
aws_config = pulumi.Config("aws")
aws_region = aws_config.require("region")
aws_secret_arn_prefix = pulumi.Output.format("arn:aws:secretsmanager:{}:{}:secret", aws_region, account_id)

base.BaseTags().auto_tag()

#
# Networking
#

vpc = aws.ec2.Vpc(
    f"{app_name}-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_support=True,
    enable_dns_hostnames=True,
    tags={
        "Name": f"{app_name}-vpc",
    },
)

igw = aws.ec2.InternetGateway(
    f"{app_name}-igw",
    vpc_id=vpc.id,
    tags={
        "Name": f"{app_name}-igw",
    },
)

public_subnet_1 = aws.ec2.Subnet(
    f"{app_name}-public-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=True,
    availability_zone="us-east-1a",
    tags={
        "Name": f"{app_name}-public-subnet-a",
    },
)
public_subnet_2 = aws.ec2.Subnet(
    f"{app_name}-public-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    map_public_ip_on_launch=True,
    availability_zone="us-east-1b",
    tags={
        "Name": f"{app_name}-public-subnet-b",
    },
)

private_subnet_1 = aws.ec2.Subnet(
    f"{app_name}-private-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.5.0/24",
    availability_zone="us-east-1a",
    tags={
        "Name": f"{app_name}-private-subnet-1",
    },
)
private_subnet_2 = aws.ec2.Subnet(
    f"{app_name}-private-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.6.0/24",
    availability_zone="us-east-1b",
    tags={
        "Name": f"{app_name}-private-subnet-2",
    },
)

public_subnet_ids = [public_subnet_1.id, public_subnet_2.id]
private_subnet_ids = [private_subnet_1.id, private_subnet_2.id]

private_route_table = aws.ec2.RouteTable(
    f"{app_name}-private-rt",
    vpc_id=vpc.id,
    tags={
        "Name": f"{app_name}-private-rt",
    },
)

aws.ec2.RouteTableAssociation(
    f"{app_name}-private-rta-1",
    subnet_id=private_subnet_1.id,
    route_table_id=private_route_table.id,
)

aws.ec2.RouteTableAssociation(
    f"{app_name}-private-rta-2",
    subnet_id=private_subnet_2.id,
    route_table_id=private_route_table.id,
)

public_route_table = aws.ec2.RouteTable(
    f"{app_name}-public-rt",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            # use this IGW to reach the internet:
            gateway_id=igw.id,
        )
    ],
    tags={
        "Name": f"{app_name}-public-rt",
    },
)

aws.ec2.RouteTableAssociation(
    f"{app_name}-public-rta-1",
    subnet_id=public_subnet_1.id,
    route_table_id=public_route_table.id,
)

aws.ec2.RouteTableAssociation(
    f"{app_name}-public-rta-2",
    subnet_id=public_subnet_2.id,
    route_table_id=public_route_table.id,
)

eip = aws.ec2.Eip(
    f"{app_name}-nat-eip",
    domain="vpc",
    tags={
        "Name": f"{app_name}-nat-eip",
    },
)

nat_gateway = aws.ec2.NatGateway(
    f"{app_name}-nat_gateway",
    allocation_id=eip.id,
    subnet_id=public_subnet_1.id,
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

aws.ec2.Route(
    f"{app_name}-nat-route",
    route_table_id=private_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    nat_gateway_id=nat_gateway.id,
)

flow_logs_role = aws.iam.Role(
    f"{app_name}-vpc-flow-logs-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "vpc-flow-logs.amazonaws.com"},
                    "Effect": "Allow",
                    "Sid": "",
                }
            ],
        }
    ),
)

flow_logs_policy = aws.iam.RolePolicy(
    f"{app_name}-vpc-flow-logs-policy",
    role=flow_logs_role.id,
    policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams",
                    ],
                    "Effect": "Allow",
                    "Resource": "*",
                }
            ],
        }
    ),
)

vpc_flow_logs = aws.ec2.FlowLog(
    f"{app_name}-vpc-flow-logs",
    iam_role_arn=flow_logs_role.arn,
    log_destination_type="cloud-watch-logs",
    traffic_type="ALL",
    vpc_id=vpc.id,
    log_destination=aws.cloudwatch.LogGroup(f"{app_name}-vpc-flow-logs-lg").arn,
)

app_security_group = aws.ec2.SecurityGroup(
    f"{app_name}-sg",
    vpc_id=vpc.id,
    description=f"{app_name} security group",
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            description="Allow all to localhost to remove default allow all egress",
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["127.0.0.1/32"],
        ),
        aws.ec2.SecurityGroupEgressArgs(
            description="Allow to all on port 80",
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupEgressArgs(
            description="Allow to all on port 443",
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
)

secrets_manager_sg = aws.ec2.SecurityGroup(
    "secretsManagerSg",
    vpc_id=vpc.id,
    description="SG for Secrets Manager VPC Endpoint",
    ingress=[
        {"from_port": 443, "to_port": 443, "protocol": "tcp", "security_groups": [app_security_group.id]},
    ],
    egress=[
        {"from_port": 0, "to_port": 0, "protocol": "-1", "cidr_blocks": ["0.0.0.0/0"]},
    ],
)

vpc_endpoint = aws.ec2.VpcEndpoint(
    "secretsManagerEndpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{aws.config.region}.secretsmanager",
    vpc_endpoint_type="Interface",
    subnet_ids=private_subnet_ids,
    security_group_ids=[secrets_manager_sg.id],
    private_dns_enabled=True,
)

s3_vpc_endpoint = aws.ec2.VpcEndpoint(
    "s3VpcEndpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{aws.config.region}.s3",
    vpc_endpoint_type="Gateway",  # S3 typically uses a Gateway Endpoint
    route_table_ids=[private_route_table.id],
    tags={
        "Name": f"{app_name}-s3-vpc-endpoint",
    },
)

#
# S3 Bucket
#

app_sse_encryption_by_default = (
    aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
        kms_master_key_id="alias/aws/s3",
        sse_algorithm="aws:kms",
    )
)

app_bucket = aws.s3.Bucket(
    f"{app_name}-bucket",
    acl="private",
    # bucket=f"{app_name}-bucket",
    server_side_encryption_configuration=aws.s3.BucketServerSideEncryptionConfigurationArgs(
        rule=aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
            apply_server_side_encryption_by_default=app_sse_encryption_by_default,
        ),
    ),
)

aws.s3.BucketPublicAccessBlockArgs(
    bucket=app_bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True,
)

#
# Application
#

ecr_repository = aws.ecr.Repository(
    f"{app_name}-image",
    image_scanning_configuration={
        "scan_on_push": True,
    },
    image_tag_mutability="MUTABLE",
)

aws.ecr.LifecyclePolicy(
    f"{app_name}-lifecycle-policy",
    repository=ecr_repository.name,
    policy=json.dumps(
        {
            "rules": [
                {
                    "rulePriority": 1,
                    "description": "Only keep the 10 most recent images",
                    "selection": {
                        "tagStatus": "any",
                        "countType": "imageCountMoreThan",
                        "countNumber": 10,
                    },
                    "action": {"type": "expire"},
                },
            ]
        }
    ),
)


def get_registry_info(registry_id, repository_url):
    """Get the registry info for an ECR repository."""
    return pulumi.Output.all(registry_id, repository_url).apply(
        lambda args: {
            "server": aws.ecr.get_authorization_token(registry_id=args[0]).proxy_endpoint,
            "username": base64.b64decode(aws.ecr.get_authorization_token(registry_id=args[0]).authorization_token)
            .decode("utf-8")
            .split(":")[0],
            "password": base64.b64decode(aws.ecr.get_authorization_token(registry_id=args[0]).authorization_token)
            .decode("utf-8")
            .split(":")[1],
        }
    )


registry_info = pulumi.Output.all(ecr_repository.registry_id, ecr_repository.repository_url).apply(
    lambda args: get_registry_info(args[0], args[1])
)

docker_image_lambda_api_handler = docker.Image(
    f"{app_name}-lambda-api-handler-image",
    build=docker.DockerBuildArgs(
        args={
            "LAMBDA_HANDLER": "arti_ai.lambda_api_handler.handler",
        },
        context="../..",
        dockerfile="../../Dockerfile",
        platform="linux/amd64",
    ),
    image_name=pulumi.Output.concat(ecr_repository.repository_url, ":lambda-api-handler"),
    skip_push=False,
    registry=registry_info,
)

docker_image_lambda_event_handler = docker.Image(
    f"{app_name}-lambda-event-handler-image",
    build=docker.DockerBuildArgs(
        args={
            "LAMBDA_HANDLER": "arti_ai.lambda_event_handler.handler",
        },
        context="../..",
        dockerfile="../../Dockerfile",
        platform="linux/amd64",
    ),
    image_name=pulumi.Output.concat(ecr_repository.repository_url, ":lambda-event-handler"),
    skip_push=False,
    registry=registry_info,
)

app_lambda_role = aws.iam.Role(
    f"{app_name}-lambda-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                }
            ],
        }
    ),
    managed_policy_arns=["arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"],
)

lambda_environment = pulumi.Output.all(
    app_bucket.id,  # type: ignore
).apply(
    lambda args: {
        "variables": {
            "APP_BUCKET_NAME": args[0],
            "APP_CONFIG_FILE": app_config_file,
            "EC_TELEMETRY": "false",
            "LOG_LEVEL": "DEBUG",
            "OPENAI_API_KEY_SECRET_NAME": openai_api_key_secret_name,
            "PINECONE_API_KEY_SECRET_NAME": pinecone_api_key_secret_name,
            "PIP_CACHE_DIR": "/tmp/pip-cache",
            "SLACK_BOT_TOKEN_SECRET_NAME": slack_bot_token_secret_name,
        }
    }
)

common_lambda_options = {
    "architectures": ["x86_64"],
    "memory_size": 2048,
    "package_type": "Image",
    "publish": True,
    "role": app_lambda_role.arn,
    "timeout": lambda_execution_timeout,
    "tracing_config": {"mode": "Active"},
    "vpc_config": {
        "security_group_ids": [app_security_group.id],
        "subnet_ids": private_subnet_ids,
    },
}

# Create the API Handler Lambda function
app_api_lambda = aws.lambda_.Function(
    resource_name=f"{app_name}-lambda",
    environment=lambda_environment,
    image_uri=docker_image_lambda_api_handler.repo_digest,
    opts=pulumi.ResourceOptions(depends_on=[docker_image_lambda_api_handler]),
    **common_lambda_options,
)

# Create the Event Handler Lambda function
app_event_lambda = aws.lambda_.Function(
    resource_name=f"{app_name}-event-lambda",
    environment=lambda_environment,
    image_uri=docker_image_lambda_event_handler.repo_digest,
    opts=pulumi.ResourceOptions(depends_on=[docker_image_lambda_event_handler]),
    **common_lambda_options,
)

secrets_manager_policy = aws.iam.RolePolicy(
    f"{app_name}-secrets-manager-policy",
    role=app_lambda_role.name,
    policy=pulumi.Output.all(aws_secret_arn_prefix).apply(  # type: ignore
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "secretsmanager:GetSecretValue",
                        "Effect": "Allow",
                        "Resource": [
                            f"{args[0]}:{openai_api_key_secret_name}-??????",
                            f"{args[0]}:{pinecone_api_key_secret_name}-??????",
                            f"{args[0]}:{slack_bot_token_secret_name}-??????",
                        ],
                    }
                ],
            }
        )
    ),
)

lambda_invoke_policy = aws.iam.RolePolicy(
    f"{app_name}-lambda-invoke-policy",
    role=app_lambda_role.name,
    policy=pulumi.Output.all(app_api_lambda.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "lambda:InvokeFunction",
                        "Effect": "Allow",
                        "Resource": args[0],
                    }
                ],
            }
        )
    ),
)

s3_bucket_policy = aws.iam.RolePolicy(
    f"{app_name}-s3-bucket-policy",
    role=app_lambda_role.name,
    policy=pulumi.Output.all(app_bucket.arn, app_event_lambda.arn).apply(
        lambda args: json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "S3ManageBuckets",
                        "Effect": "Allow",
                        "Action": ["s3:HeadBucket", "s3:ListBucket", "s3:GetBucketLocation"],
                        "Resource": args[0],
                    },
                    {
                        "Sid": "S3ManageObjects",
                        "Effect": "Allow",
                        "Action": [
                            "s3:GetObject",
                            "s3:GetObjectTagging",
                            "s3:PutObject",
                            "s3:PutObjectTagging",
                        ],
                        "Resource": f"{args[0]}/*",
                    },
                ],
            }
        )
    ),
)

#
# EventBridge
#

event_rule_schedule = aws.cloudwatch.EventRule(
    f"{app_name}-event-rule-schedule",
    schedule_expression=data_load_event_rule_schedule,
    state=data_load_event_rule_state,
)

event_rule_target = aws.cloudwatch.EventTarget(
    f"{app_name}-event-target-schedule",
    rule=event_rule_schedule.name,
    arn=app_event_lambda.arn,
)

event_rule_target_permission = aws.lambda_.Permission(
    f"{app_name}-lambda-event-target-permissions-schedule",
    action="lambda:InvokeFunction",
    function=app_event_lambda.name,
    principal="events.amazonaws.com",
    source_arn=event_rule_schedule.arn,
)

#
# API
#

api = aws.apigateway.RestApi(
    f"{app_name}-api",
    description="HTTP proxy to a Lambda function",
    binary_media_types=["*/*"],
)

root_method = aws.apigateway.Method(
    f"{app_name}-api-method-root",
    rest_api=api.id,
    resource_id=api.root_resource_id,
    http_method="ANY",
    authorization="NONE",
)

integration_root = aws.apigateway.Integration(
    f"{app_name}-api-integration-root",
    rest_api=api.id,
    resource_id=api.root_resource_id,
    http_method=root_method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=app_api_lambda.invoke_arn,
)

proxy_resource = aws.apigateway.Resource(
    f"{app_name}-api-resource-proxy", parent_id=api.root_resource_id, path_part="{proxy+}", rest_api=api.id
)

proxy_method = aws.apigateway.Method(
    f"{app_name}-api-method-proxy",
    rest_api=api.id,
    resource_id=proxy_resource.id,
    http_method="ANY",
    authorization="NONE",
    request_parameters={
        "method.request.path.proxy": True,
    },
)

integration_proxy = aws.apigateway.Integration(
    f"{app_name}-api-integration-proxy",
    rest_api=api.id,
    resource_id=proxy_resource.id,
    http_method=proxy_method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=app_api_lambda.invoke_arn,
)

aws.lambda_.Permission(
    f"{app_name}-api-lambda-permission",
    action="lambda:InvokeFunction",
    principal="apigateway.amazonaws.com",
    function=app_api_lambda.name,
    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*"),
)

aws.lambda_.Permission(
    f"{app_name}-api-lambda-permission-2",
    action="lambda:InvokeFunction",
    principal="apigateway.amazonaws.com",
    function=app_api_lambda.name,
    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*/{proxy+}"),
)

deployment = aws.apigateway.Deployment(
    f"{app_name}-api-deployment",
    rest_api=api.id,
    triggers={"config-hash": api.body.apply(lambda body: hashlib.sha1(json.dumps(body).encode()).hexdigest())},
    opts=pulumi.ResourceOptions(depends_on=[integration_root, integration_proxy]),
)

api_gateway_cloudwatch_role = aws.iam.Role(
    f"{app_name}-api-gateway-cloudwatch-role",
    assume_role_policy=json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "apigateway.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    ),
    managed_policy_arns=["arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"],
)


def create_api_log_group(args):
    """Create a CloudWatch log group for the API."""
    api_id, api_stage = args
    return aws.cloudwatch.LogGroup(
        f"{app_name}-api-lg", name=f"API-Gateway-Execution-Logs_{api_id}/{api_stage}", retention_in_days=14
    )


api_log_group = pulumi.Output.all(api.id, "stage").apply(create_api_log_group)

stage = aws.apigateway.Stage(
    f"{app_name}-api-stage",
    deployment=deployment.id,
    rest_api=api.id,
    stage_name="stage",
    access_log_settings=aws.apigateway.StageAccessLogSettingsArgs(
        destination_arn=api_log_group.arn,
        format=json.dumps(
            {
                "requestId": "$context.requestId",
                "ip": "$context.identity.sourceIp",
                "caller": "$context.identity.caller",
                "user": "$context.identity.user",
                "requestTime": "$context.requestTime",
                "httpMethod": "$context.httpMethod",
                "resourcePath": "$context.resourcePath",
                "status": "$context.status",
                "protocol": "$context.protocol",
                "responseLength": "$context.responseLength",
            }
        ),
    ),
    variables={"cloudwatchRoleArn": api_gateway_cloudwatch_role.arn},
)

metrics = aws.apigateway.MethodSettings(
    f"{app_name}-api-metrics",
    rest_api=api.id,
    stage_name=stage.stage_name,
    method_path="*/*",  # Apply to all methods
    settings=aws.apigateway.MethodSettingsSettingsArgs(metrics_enabled=True, logging_level="INFO"),
)


def create_lambda_log_group(args):
    """Create a CloudWatch log group for the Lambda function."""
    lambda_function_name = args[0]
    return aws.cloudwatch.LogGroup(f"{app_name}-lg", name=f"/aws/lambda/{lambda_function_name}", retention_in_days=14)


app_log_group = pulumi.Output.all(app_api_lambda.name).apply(create_lambda_log_group)

#
# Pinecone
#
#
pinecone_index = pinecone.PineconeIndex(
    f"{app_name}-pinecone-index",
    name="main-index",
    dimension=1536,
    metric=pinecone.IndexMetric.COSINE,
    spec=pinecone.PineconeSpecArgs(
        pod=pinecone.PineconePodSpecArgs(
            environment="gcp-starter",
            pod_type="starter",
            replicas=1,
        )
    ),
    opts=pulumi.ResourceOptions(delete_before_replace=True),
)

# pulumi.export("output", {"value": arti_pinecone_index.host})

#
# Outputs
#

pulumi.export("api_log_group", api_log_group.id)
pulumi.export("app_log_group", app_log_group.id)
pulumi.export("app_event_lambda_id", app_event_lambda.id)
pulumi.export("app_api_lambda_id", app_api_lambda.id)
pulumi.export("docker_image_lambda_api_repo_digest", docker_image_lambda_api_handler.repo_digest)
pulumi.export("docker_image_lambda_event_repo_digest", docker_image_lambda_event_handler.repo_digest)
pulumi.export("invoke_url", deployment.invoke_url)
pulumi.export("public_subnet_ids", public_subnet_ids)
pulumi.export("private_subnet_ids", private_subnet_ids)
