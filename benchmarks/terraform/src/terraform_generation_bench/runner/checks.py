"""Post-apply checks: verify resources exist and wiring is correct."""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import boto3
from botocore.exceptions import ClientError

from .utils import log_info, log_error, log_warn, export_localstack_env, load_spec


def run_checks(work_dir: Path, task_id: str) -> Dict[str, Any]:
    """Run post-apply checks on terraform resources.
    
    Args:
        work_dir: Directory containing terraform outputs.
        task_id: Task ID to filter resources by.
        
    Returns:
        Dictionary with check results.
    """
    log_info(f"Running checks for task: {task_id}")
    
    # Export LocalStack environment
    export_localstack_env()
    
    # Load task spec to understand what to check
    spec_file = Path(f"tasks/terraform_generation/{task_id}/spec.yaml")
    if not spec_file.exists():
        log_error(f"Spec file not found: {spec_file}")
        return {
            "task_id": task_id,
            "pass": False,
            "errors": [f"Spec file not found: {spec_file}"]
        }
    
    spec = load_spec(spec_file)
    expected_checks = spec.get('checks', {})
    
    # Get terraform outputs
    outputs_file = work_dir / "outputs.json"
    if not outputs_file.exists():
        log_error("outputs.json not found. Run terraform output -json first.")
        return {
            "task_id": task_id,
            "pass": False,
            "errors": ["outputs.json not found"]
        }
    
    with open(outputs_file, 'r') as f:
        outputs = json.load(f)
    
    # Initialize check results
    pass_check = True
    errors: List[str] = []
    details: Dict[str, Any] = {}
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    
    # Setup boto3 clients for LocalStack
    ec2_client = boto3.client(
        'ec2',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    s3_client = boto3.client(
        's3',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    iam_client = boto3.client(
        'iam',
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='test',
        aws_secret_access_key='test'
    )
    
    # Route checks based on task type
    if task_id == "task_vpc_3subnets_3ec2":
        pass_check, errors, counts, wiring, details = _check_vpc_3subnets_3ec2(
            ec2_client, outputs, task_id, expected_checks
        )
    elif task_id.startswith("task_s3"):
        pass_check, errors, counts, wiring, details = _check_s3_tasks(
            s3_client, outputs, task_id, expected_checks, spec
        )
    elif task_id == "task_security_group_complex":
        pass_check, errors, counts, wiring, details = _check_security_group(
            ec2_client, outputs, task_id, expected_checks
        )
    elif task_id == "task_iam_role_policy":
        pass_check, errors, counts, wiring, details = _check_iam_role_policy(
            iam_client, outputs, task_id, expected_checks
        )
    elif task_id == "task_vpc_internet_gateway":
        pass_check, errors, counts, wiring, details = _check_vpc_internet_gateway(
            ec2_client, outputs, task_id, expected_checks
        )
    elif task_id == "task_vpc_nat_gateway":
        pass_check, errors, counts, wiring, details = _check_vpc_nat_gateway(
            ec2_client, outputs, task_id, expected_checks
        )
    elif task_id == "task_ec2_instance_profile":
        pass_check, errors, counts, wiring, details = _check_ec2_instance_profile(
            ec2_client, iam_client, outputs, task_id, expected_checks
        )
    elif task_id == "task_vpc_multiple_route_tables":
        pass_check, errors, counts, wiring, details = _check_vpc_multiple_route_tables(
            ec2_client, outputs, task_id, expected_checks
        )
    else:
        log_warn(f"No specific checks defined for task {task_id}, running basic validation")
        pass_check, errors, counts, wiring, details = _check_generic(
            outputs, task_id, expected_checks
        )
    
    # Build result
    result = {
        "task_id": task_id,
        "pass": pass_check,
        "details": details,
        "counts": counts,
        "wiring": wiring,
        "errors": errors
    }
    
    # Write check.json
    check_file = work_dir / "check.json"
    with open(check_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    if pass_check:
        log_info("All checks passed!")
    else:
        log_error(f"Checks failed. See {check_file} for details.")
    
    return result


def _check_vpc_3subnets_3ec2(ec2_client, outputs: Dict, task_id: str, 
                              expected_checks: Dict) -> tuple:
    """Check VPC with 3 subnets and 3 EC2 instances."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    vpc_id = outputs.get('vpc_id', {}).get('value')
    subnet_ids = outputs.get('subnet_ids', {}).get('value', [])
    instance_ids = outputs.get('instance_ids', {}).get('value', [])
    
    if not vpc_id or vpc_id == "null":
        return False, ["VPC ID not found in outputs"], {}, {}, {}
    
    details['vpc_id'] = vpc_id
    details['subnet_ids'] = subnet_ids
    details['instance_ids'] = instance_ids
    
    # Check VPC
    try:
        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        vpc_count = len(vpc_response['Vpcs'])
        expected_vpc = expected_checks.get('vpc_count', 1)
        if vpc_count != expected_vpc:
            log_error(f"Expected {expected_vpc} VPC, found {vpc_count}")
            pass_check = False
            errors.append(f"Expected {expected_vpc} VPC, found {vpc_count}")
        counts['vpc'] = vpc_count
    except ClientError as e:
        log_error(f"Failed to describe VPC: {e}")
        return False, [f"Failed to describe VPC: {str(e)}"], {}, {}, {}
    
    # Check subnets
    try:
        subnet_response = ec2_client.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'tag:task_id', 'Values': [task_id]}
            ]
        )
        subnet_count = len(subnet_response['Subnets'])
        expected_subnets = expected_checks.get('subnet_count', 3)
        if subnet_count != expected_subnets:
            log_error(f"Expected {expected_subnets} subnets, found {subnet_count}")
            pass_check = False
            errors.append(f"Expected {expected_subnets} subnets, found {subnet_count}")
        counts['subnet'] = subnet_count
        
        for subnet in subnet_response['Subnets']:
            if subnet['VpcId'] != vpc_id:
                pass_check = False
                errors.append("Subnet wiring error: subnet not in expected VPC")
        wiring['subnets_in_vpc'] = True
    except ClientError as e:
        log_error(f"Failed to describe subnets: {e}")
        pass_check = False
        errors.append(f"Failed to describe subnets: {str(e)}")
    
    # Check instances
    try:
        instance_response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:task_id', 'Values': [task_id]},
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]
        )
        instances = []
        for reservation in instance_response['Reservations']:
            instances.extend(reservation['Instances'])
        
        instance_count = len(instances)
        expected_instances = expected_checks.get('instance_count', 3)
        if instance_count != expected_instances:
            log_error(f"Expected {expected_instances} instances, found {instance_count}")
            pass_check = False
            errors.append(f"Expected {expected_instances} instances, found {instance_count}")
        counts['instance'] = instance_count
        
        found_subnet_ids = set(inst['SubnetId'] for inst in instances)
        expected_subnet_ids = set(subnet_ids)
        if not found_subnet_ids.issubset(expected_subnet_ids):
            pass_check = False
            errors.append("Instance wiring error: instance in unexpected subnet")
        wiring['instances_in_subnets'] = True
    except ClientError as e:
        log_error(f"Failed to describe instances: {e}")
        pass_check = False
        errors.append(f"Failed to describe instances: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_s3_tasks(s3_client, outputs: Dict, task_id: str, 
                    expected_checks: Dict, spec: Dict) -> tuple:
    """Check S3 bucket tasks."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    bucket_id = outputs.get('bucket_id', {}).get('value') or outputs.get('bucket_name', {}).get('value')
    bucket_arn = outputs.get('bucket_arn', {}).get('value')
    
    if not bucket_id:
        return False, ["Bucket ID/name not found in outputs"], {}, {}, {}
    
    details['bucket_id'] = bucket_id
    details['bucket_arn'] = bucket_arn
    
    # Check bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_id)
        counts['bucket'] = 1
        log_info(f"Bucket {bucket_id} exists")
    except ClientError as e:
        log_error(f"Bucket {bucket_id} does not exist: {e}")
        return False, [f"Bucket {bucket_id} does not exist: {str(e)}"], {}, {}, {}
    
    # Check versioning if expected
    if expected_checks.get('versioning_enabled'):
        try:
            versioning = s3_client.get_bucket_versioning(Bucket=bucket_id)
            versioning_status = versioning.get('Status', '')
            if versioning_status != 'Enabled':
                log_error(f"Expected versioning to be Enabled, found {versioning_status}")
                pass_check = False
                errors.append(f"Versioning not enabled: {versioning_status}")
            details['versioning_status'] = versioning_status
        except ClientError as e:
            log_warn(f"Could not check versioning: {e}")
    
    # Check lifecycle rules if expected
    if expected_checks.get('lifecycle_rule_count'):
        try:
            lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_id)
            rule_count = len(lifecycle.get('Rules', []))
            expected_rules = expected_checks.get('lifecycle_rule_count', 1)
            if rule_count != expected_rules:
                log_error(f"Expected {expected_rules} lifecycle rules, found {rule_count}")
                pass_check = False
                errors.append(f"Expected {expected_rules} lifecycle rules, found {rule_count}")
            counts['lifecycle_rule'] = rule_count
            wiring['lifecycle_rule_attached'] = True
        except ClientError as e:
            if 'NoSuchLifecycleConfiguration' not in str(e):
                log_warn(f"Could not check lifecycle: {e}")
            if expected_checks.get('lifecycle_rule_count'):
                pass_check = False
                errors.append("Lifecycle configuration not found")
    
    # Check public access block if expected
    if expected_checks.get('public_access_block_count'):
        try:
            pab = s3_client.get_public_access_block(Bucket=bucket_id)
            pab_config = pab.get('PublicAccessBlockConfiguration', {})
            counts['public_access_block'] = 1
            details['public_access_block'] = pab_config
            wiring['public_access_block_attached'] = True
        except ClientError as e:
            if 'NoSuchPublicAccessBlockConfiguration' not in str(e):
                log_warn(f"Could not check public access block: {e}")
            if expected_checks.get('public_access_block_count'):
                pass_check = False
                errors.append("Public access block not found")
    
    # Check bucket policy if expected
    if expected_checks.get('bucket_policy_count'):
        try:
            policy = s3_client.get_bucket_policy(Bucket=bucket_id)
            counts['bucket_policy'] = 1
            details['bucket_policy'] = policy.get('Policy')
            wiring['bucket_policy_attached'] = True
        except ClientError as e:
            if 'NoSuchBucketPolicy' not in str(e):
                log_warn(f"Could not check bucket policy: {e}")
            if expected_checks.get('bucket_policy_count'):
                pass_check = False
                errors.append("Bucket policy not found")
    
    # Check CORS configuration if expected
    if expected_checks.get('cors_configuration_count'):
        try:
            cors = s3_client.get_bucket_cors(Bucket=bucket_id)
            cors_rules = cors.get('CORSRules', [])
            if len(cors_rules) > 0:
                counts['cors_configuration'] = 1
                details['cors_rules'] = cors_rules
                wiring['cors_configuration_attached'] = True
            else:
                if expected_checks.get('cors_configuration_count'):
                    pass_check = False
                    errors.append("CORS configuration not found or empty")
        except ClientError as e:
            if 'NoSuchCORSConfiguration' not in str(e):
                log_warn(f"Could not check CORS configuration: {e}")
            if expected_checks.get('cors_configuration_count'):
                pass_check = False
                errors.append("CORS configuration not found")
    
    return pass_check, errors, counts, wiring, details


def _check_security_group(ec2_client, outputs: Dict, task_id: str, 
                          expected_checks: Dict) -> tuple:
    """Check security group task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    vpc_id = outputs.get('vpc_id', {}).get('value')
    security_group_id = outputs.get('security_group_id', {}).get('value')
    
    if not vpc_id or not security_group_id:
        return False, ["VPC ID or Security Group ID not found in outputs"], {}, {}, {}
    
    details['vpc_id'] = vpc_id
    details['security_group_id'] = security_group_id
    
    # Check VPC
    try:
        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        vpc_count = len(vpc_response['Vpcs'])
        expected_vpc = expected_checks.get('vpc_count', 1)
        if vpc_count != expected_vpc:
            pass_check = False
            errors.append(f"Expected {expected_vpc} VPC, found {vpc_count}")
        counts['vpc'] = vpc_count
    except ClientError as e:
        return False, [f"Failed to describe VPC: {str(e)}"], {}, {}, {}
    
    # Check security group
    try:
        sg_response = ec2_client.describe_security_groups(
            GroupIds=[security_group_id],
            Filters=[{'Name': 'tag:task_id', 'Values': [task_id]}]
        )
        sg_count = len(sg_response['SecurityGroups'])
        expected_sg = expected_checks.get('security_group_count', 1)
        if sg_count != expected_sg:
            pass_check = False
            errors.append(f"Expected {expected_sg} security group, found {sg_count}")
        counts['security_group'] = sg_count
        
        if sg_count > 0:
            sg = sg_response['SecurityGroups'][0]
            if sg['VpcId'] != vpc_id:
                pass_check = False
                errors.append("Security group not in expected VPC")
            wiring['security_group_in_vpc'] = True
            
            # Check ingress rules
            ingress_count = len(sg.get('IpPermissions', []))
            expected_ingress = expected_checks.get('ingress_rule_count', 0)
            if ingress_count != expected_ingress:
                pass_check = False
                errors.append(f"Expected {expected_ingress} ingress rules, found {ingress_count}")
            counts['ingress_rule'] = ingress_count
            
            # Check egress rules
            egress_count = len(sg.get('IpPermissionsEgress', []))
            expected_egress = expected_checks.get('egress_rule_count', 0)
            if egress_count != expected_egress:
                pass_check = False
                errors.append(f"Expected {expected_egress} egress rules, found {egress_count}")
            counts['egress_rule'] = egress_count
    except ClientError as e:
        pass_check = False
        errors.append(f"Failed to describe security group: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_iam_role_policy(iam_client, outputs: Dict, task_id: str, 
                           expected_checks: Dict) -> tuple:
    """Check IAM role and policy task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    role_arn = outputs.get('role_arn', {}).get('value')
    policy_arn = outputs.get('policy_arn', {}).get('value')
    
    if not role_arn:
        return False, ["Role ARN not found in outputs"], {}, {}, {}
    
    details['role_arn'] = role_arn
    details['policy_arn'] = policy_arn
    
    # Extract role name from ARN
    role_name = role_arn.split('/')[-1] if '/' in role_arn else role_arn
    
    # Check role exists
    try:
        role_response = iam_client.get_role(RoleName=role_name)
        counts['role'] = 1
        details['role'] = role_response['Role']
        
        # Check trust policy allows EC2
        trust_policy = role_response['Role']['AssumeRolePolicyDocument']
        # Simple check - look for ec2.amazonaws.com in the policy
        trust_policy_str = json.dumps(trust_policy) if isinstance(trust_policy, dict) else str(trust_policy)
        if 'ec2.amazonaws.com' in trust_policy_str.lower():
            wiring['trust_policy_allows_ec2'] = True
        else:
            pass_check = False
            errors.append("Trust policy does not allow EC2 service")
    except ClientError as e:
        return False, [f"Failed to get role: {str(e)}"], {}, {}, {}
    
    # Check policy exists if provided
    if policy_arn:
        try:
            # Extract policy name from ARN
            policy_name = policy_arn.split('/')[-1] if '/' in policy_arn else policy_arn
            policy_response = iam_client.get_policy(PolicyArn=policy_arn)
            counts['policy'] = 1
        except ClientError as e:
            log_warn(f"Could not get policy: {e}")
            if expected_checks.get('policy_count'):
                pass_check = False
                errors.append(f"Policy not found: {str(e)}")
    
    # Check role policy attachment
    try:
        attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
        attachment_count = len(attached_policies.get('AttachedPolicies', []))
        expected_attachments = expected_checks.get('role_policy_attachment_count', 0)
        if expected_attachments > 0 and attachment_count < expected_attachments:
            pass_check = False
            errors.append(f"Expected {expected_attachments} policy attachments, found {attachment_count}")
        counts['role_policy_attachment'] = attachment_count
        if attachment_count > 0:
            wiring['policy_attached_to_role'] = True
    except ClientError as e:
        log_warn(f"Could not list attached policies: {e}")
    
    return pass_check, errors, counts, wiring, details


def _check_vpc_internet_gateway(ec2_client, outputs: Dict, task_id: str, 
                                expected_checks: Dict) -> tuple:
    """Check VPC with Internet Gateway task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    vpc_id = outputs.get('vpc_id', {}).get('value')
    internet_gateway_id = outputs.get('internet_gateway_id', {}).get('value')
    route_table_id = outputs.get('route_table_id', {}).get('value')
    subnet_id = outputs.get('subnet_id', {}).get('value')
    
    if not vpc_id:
        return False, ["VPC ID not found in outputs"], {}, {}, {}
    
    details['vpc_id'] = vpc_id
    details['internet_gateway_id'] = internet_gateway_id
    details['route_table_id'] = route_table_id
    details['subnet_id'] = subnet_id
    
    # Check VPC
    try:
        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        vpc_count = len(vpc_response['Vpcs'])
        expected_vpc = expected_checks.get('vpc_count', 1)
        if vpc_count != expected_vpc:
            pass_check = False
            errors.append(f"Expected {expected_vpc} VPC, found {vpc_count}")
        counts['vpc'] = vpc_count
    except ClientError as e:
        return False, [f"Failed to describe VPC: {str(e)}"], {}, {}, {}
    
    # Check Internet Gateway
    if internet_gateway_id:
        try:
            igw_response = ec2_client.describe_internet_gateways(
                InternetGatewayIds=[internet_gateway_id]
            )
            igw_count = len(igw_response['InternetGateways'])
            expected_igw = expected_checks.get('internet_gateway_count', 1)
            if igw_count != expected_igw:
                pass_check = False
                errors.append(f"Expected {expected_igw} Internet Gateway, found {igw_count}")
            counts['internet_gateway'] = igw_count
            
            # Check IGW is attached to VPC
            if igw_count > 0:
                igw = igw_response['InternetGateways'][0]
                attachments = igw.get('Attachments', [])
                vpc_attached = any(att.get('VpcId') == vpc_id for att in attachments)
                if vpc_attached:
                    wiring['internet_gateway_attached_to_vpc'] = True
                else:
                    pass_check = False
                    errors.append("Internet Gateway not attached to VPC")
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to describe Internet Gateway: {str(e)}")
    
    # Check Route Table
    if route_table_id:
        try:
            rt_response = ec2_client.describe_route_tables(
                RouteTableIds=[route_table_id]
            )
            rt_count = len(rt_response['RouteTables'])
            expected_rt = expected_checks.get('route_table_count', 1)
            if rt_count != expected_rt:
                pass_check = False
                errors.append(f"Expected {expected_rt} Route Table, found {rt_count}")
            counts['route_table'] = rt_count
            
            # Check default route to IGW
            if rt_count > 0:
                rt = rt_response['RouteTables'][0]
                routes = rt.get('Routes', [])
                default_route = next((r for r in routes if r.get('DestinationCidrBlock') == '0.0.0.0/0'), None)
                if default_route and default_route.get('GatewayId') == internet_gateway_id:
                    wiring['route_table_has_default_route_to_igw'] = True
                else:
                    pass_check = False
                    errors.append("Route Table missing default route to Internet Gateway")
                
                # Check subnet association
                associations = rt.get('Associations', [])
                subnet_associated = any(assoc.get('SubnetId') == subnet_id for assoc in associations)
                if subnet_associated:
                    wiring['subnet_associated_with_route_table'] = True
                else:
                    pass_check = False
                    errors.append("Subnet not associated with Route Table")
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to describe Route Table: {str(e)}")
    
    # Check Subnet
    if subnet_id:
        try:
            subnet_response = ec2_client.describe_subnets(
                SubnetIds=[subnet_id],
                Filters=[{'Name': 'tag:task_id', 'Values': [task_id]}]
            )
            subnet_count = len(subnet_response['Subnets'])
            expected_subnet = expected_checks.get('subnet_count', 1)
            if subnet_count != expected_subnet:
                pass_check = False
                errors.append(f"Expected {expected_subnet} subnet, found {subnet_count}")
            counts['subnet'] = subnet_count
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to describe Subnet: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_vpc_nat_gateway(ec2_client, outputs: Dict, task_id: str, 
                           expected_checks: Dict) -> tuple:
    """Check VPC with NAT Gateway task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    vpc_id = outputs.get('vpc_id', {}).get('value')
    nat_gateway_id = outputs.get('nat_gateway_id', {}).get('value')
    public_subnet_id = outputs.get('public_subnet_id', {}).get('value')
    private_subnet_id = outputs.get('private_subnet_id', {}).get('value')
    
    if not vpc_id:
        return False, ["VPC ID not found in outputs"], {}, {}, {}
    
    details['vpc_id'] = vpc_id
    details['nat_gateway_id'] = nat_gateway_id
    
    # Check VPC
    try:
        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        counts['vpc'] = len(vpc_response['Vpcs'])
    except ClientError as e:
        return False, [f"Failed to describe VPC: {str(e)}"], {}, {}, {}
    
    # Check NAT Gateway
    if nat_gateway_id:
        try:
            nat_response = ec2_client.describe_nat_gateways(NatGatewayIds=[nat_gateway_id])
            nat_count = len(nat_response['NatGateways'])
            expected_nat = expected_checks.get('nat_gateway_count', 1)
            if nat_count != expected_nat:
                pass_check = False
                errors.append(f"Expected {expected_nat} NAT Gateway, found {nat_count}")
            counts['nat_gateway'] = nat_count
            
            if nat_count > 0:
                nat = nat_response['NatGateways'][0]
                if nat.get('SubnetId') == public_subnet_id:
                    wiring['nat_gateway_in_public_subnet'] = True
                else:
                    pass_check = False
                    errors.append("NAT Gateway not in public subnet")
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to describe NAT Gateway: {str(e)}")
    
    # Check route tables
    try:
        rt_response = ec2_client.describe_route_tables(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        rt_count = len(rt_response['RouteTables'])
        expected_rt = expected_checks.get('public_route_table_count', 0) + expected_checks.get('private_route_table_count', 0)
        if rt_count < expected_rt:
            pass_check = False
            errors.append(f"Expected at least {expected_rt} route tables, found {rt_count}")
        counts['route_table'] = rt_count
        
        # Check for routes
        for rt in rt_response['RouteTables']:
            routes = rt.get('Routes', [])
            default_route = next((r for r in routes if r.get('DestinationCidrBlock') == '0.0.0.0/0'), None)
            if default_route:
                if 'GatewayId' in default_route:
                    wiring['public_route_to_igw'] = True
                elif 'NatGatewayId' in default_route:
                    wiring['private_route_to_nat'] = True
    except ClientError as e:
        pass_check = False
        errors.append(f"Failed to describe Route Tables: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_ec2_instance_profile(ec2_client, iam_client, outputs: Dict, task_id: str, 
                                expected_checks: Dict) -> tuple:
    """Check EC2 instance with instance profile task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    instance_id = outputs.get('instance_id', {}).get('value')
    role_arn = outputs.get('iam_role_arn', {}).get('value')
    instance_profile_arn = outputs.get('instance_profile_arn', {}).get('value')
    
    if not instance_id:
        return False, ["Instance ID not found in outputs"], {}, {}, {}
    
    details['instance_id'] = instance_id
    details['role_arn'] = role_arn
    details['instance_profile_arn'] = instance_profile_arn
    
    # Check instance
    try:
        instance_response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instances = []
        for reservation in instance_response['Reservations']:
            instances.extend(reservation['Instances'])
        
        instance_count = len(instances)
        expected_instance = expected_checks.get('instance_count', 1)
        if instance_count != expected_instance:
            pass_check = False
            errors.append(f"Expected {expected_instance} instance, found {instance_count}")
        counts['instance'] = instance_count
        
        if instance_count > 0:
            instance = instances[0]
            if instance.get('IamInstanceProfile'):
                wiring['instance_profile_attached_to_instance'] = True
            else:
                pass_check = False
                errors.append("Instance profile not attached to instance")
    except ClientError as e:
        pass_check = False
        errors.append(f"Failed to describe instance: {str(e)}")
    
    # Check IAM role
    if role_arn:
        try:
            role_name = role_arn.split('/')[-1] if '/' in role_arn else role_arn
            role_response = iam_client.get_role(RoleName=role_name)
            counts['iam_role'] = 1
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to get IAM role: {str(e)}")
    
    # Check instance profile
    if instance_profile_arn:
        try:
            profile_name = instance_profile_arn.split('/')[-1] if '/' in instance_profile_arn else instance_profile_arn
            profile_response = iam_client.get_instance_profile(InstanceProfileName=profile_name)
            counts['instance_profile'] = 1
            if profile_response['InstanceProfile'].get('Roles'):
                wiring['role_attached_to_instance_profile'] = True
        except ClientError as e:
            pass_check = False
            errors.append(f"Failed to get instance profile: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_vpc_multiple_route_tables(ec2_client, outputs: Dict, task_id: str, 
                                     expected_checks: Dict) -> tuple:
    """Check VPC with multiple route tables task."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    vpc_id = outputs.get('vpc_id', {}).get('value')
    subnet_ids = outputs.get('subnet_ids', {}).get('value', [])
    route_table_ids = outputs.get('route_table_ids', {}).get('value', [])
    
    if not vpc_id:
        return False, ["VPC ID not found in outputs"], {}, {}, {}
    
    details['vpc_id'] = vpc_id
    details['subnet_ids'] = subnet_ids
    details['route_table_ids'] = route_table_ids
    
    # Check VPC
    try:
        vpc_response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        counts['vpc'] = len(vpc_response['Vpcs'])
    except ClientError as e:
        return False, [f"Failed to describe VPC: {str(e)}"], {}, {}, {}
    
    # Check subnets
    try:
        subnet_response = ec2_client.describe_subnets(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'tag:task_id', 'Values': [task_id]}
            ]
        )
        subnet_count = len(subnet_response['Subnets'])
        expected_subnets = expected_checks.get('subnet_count', 3)
        if subnet_count != expected_subnets:
            pass_check = False
            errors.append(f"Expected {expected_subnets} subnets, found {subnet_count}")
        counts['subnet'] = subnet_count
    except ClientError as e:
        pass_check = False
        errors.append(f"Failed to describe subnets: {str(e)}")
    
    # Check route tables
    try:
        rt_response = ec2_client.describe_route_tables(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        rt_count = len(rt_response['RouteTables'])
        expected_rt = expected_checks.get('route_table_count', 2)
        if rt_count != expected_rt:
            pass_check = False
            errors.append(f"Expected {expected_rt} route tables, found {rt_count}")
        counts['route_table'] = rt_count
        
        # Check associations
        associated_subnets = set()
        for rt in rt_response['RouteTables']:
            associations = rt.get('Associations', [])
            for assoc in associations:
                if assoc.get('SubnetId'):
                    associated_subnets.add(assoc['SubnetId'])
        
        if len(associated_subnets) == len(subnet_ids):
            wiring['all_subnets_associated_with_route_tables'] = True
        else:
            pass_check = False
            errors.append("Not all subnets are associated with route tables")
    except ClientError as e:
        pass_check = False
        errors.append(f"Failed to describe Route Tables: {str(e)}")
    
    return pass_check, errors, counts, wiring, details


def _check_generic(outputs: Dict, task_id: str, expected_checks: Dict) -> tuple:
    """Generic check for tasks without specific handlers."""
    pass_check = True
    errors: List[str] = []
    counts: Dict[str, int] = {}
    wiring: Dict[str, bool] = {}
    details: Dict[str, Any] = {}
    
    # Basic validation - just check outputs exist
    if not outputs:
        return False, ["No outputs found"], {}, {}, {}
    
    details['outputs'] = outputs
    log_warn(f"Using generic checks for {task_id} - consider adding specific checks")
    
    return pass_check, errors, counts, wiring, details
