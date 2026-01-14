# ECS Deployment Guide
## Streamlit Frontend on AWS ECS Fargate

This guide explains how to deploy the Streamlit frontend to AWS ECS (Elastic Container Service) using Fargate for serverless container management.

---

## Overview

The Terraform configuration now includes:

- **ECR Repository**: Stores Docker images
- **VPC & Networking**: Public and private subnets across 2 availability zones
- **Application Load Balancer**: Distributes traffic to ECS tasks
- **ECS Cluster & Service**: Runs Streamlit containers using Fargate
- **Auto-Scaling**: Scales based on CPU and memory utilization
- **CloudWatch**: Logs and monitoring

**Total Resources Created**: ~45 AWS resources (includes networking, ECS, and Lambda infrastructure)

---

## Prerequisites

1. **Docker installed** on your local machine or CloudShell
2. **AWS CLI configured** with appropriate credentials
3. **Terraform >= 1.0** installed
4. **Completed Lambda deployment** (API Gateway must exist)

---

## Deployment Steps

### Step 1: Deploy Infrastructure with Terraform

Navigate to the terraform directory:

```bash
cd terraform
```

Initialize and apply Terraform (if not already done):

```bash
terraform init
terraform apply
```

This will create:
- VPC with public/private subnets
- ECR repository for Docker images
- ECS cluster and task definition
- Application Load Balancer
- All Lambda functions and API Gateway

**Note**: The ECS service will initially fail to start because no Docker image exists in ECR yet.

### Step 2: Build and Push Docker Image

Use the provided build script:

```bash
./build-and-push-frontend.sh
```

This script will:
1. Authenticate Docker to your ECR repository
2. Build the Streamlit Docker image
3. Tag the image with `latest` and a timestamp
4. Push both versions to ECR

**Alternative Manual Steps**:

```bash
# Get ECR repository URL
ECR_REPO=$(terraform output -raw ecr_repository_url)
AWS_REGION=$(aws configure get region || echo "us-east-1")
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build image
cd ../frontend
docker build -t zendesk-sme-finder-frontend:latest .

# Tag and push
docker tag zendesk-sme-finder-frontend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
```

### Step 3: Force ECS Service Deployment

After pushing the image, force ECS to deploy:

```bash
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

Wait 2-3 minutes for the service to stabilize.

### Step 4: Get Frontend URL

```bash
terraform output frontend_url
```

Example output:
```
http://zendesk-sme-finder-alb-123456789.us-east-1.elb.amazonaws.com
```

Open this URL in your browser to access the Streamlit application.

---

## Architecture

### Network Architecture

```
Internet
    |
    v
Application Load Balancer (Public Subnets)
    |
    v
ECS Tasks - Streamlit (Private Subnets)
    |
    v
NAT Gateway --> API Gateway (for backend calls)
```

### ECS Configuration

- **Launch Type**: Fargate (serverless)
- **CPU**: 512 units (0.5 vCPU)
- **Memory**: 1024 MB (1 GB)
- **Desired Count**: 1 task
- **Auto-Scaling**: 1-4 tasks based on CPU/memory

### Load Balancer

- **Type**: Application Load Balancer
- **Protocol**: HTTP (port 80)
- **Health Check**: `/_stcore/health` endpoint
- **Target**: ECS tasks on port 8501

---

## Environment Variables

The ECS task automatically receives:

- `API_ENDPOINT`: API Gateway endpoint URL
- `API_KEY`: API Gateway key for authentication

These are injected by Terraform from the API Gateway outputs.

---

## Updating the Frontend

### Option 1: Rebuild and Deploy (Recommended)

```bash
cd terraform
./build-and-push-frontend.sh
```

The script will automatically trigger a new ECS deployment.

### Option 2: Manual Update

```bash
# Build and push new image
cd frontend
docker build -t zendesk-sme-finder-frontend:latest .
docker tag zendesk-sme-finder-frontend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# Force new deployment
cd ../terraform
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

---

## Monitoring

### CloudWatch Logs

View ECS logs:

```bash
aws logs tail /ecs/zendesk-sme-finder-frontend --follow
```

Or in AWS Console:
1. Go to CloudWatch > Log groups
2. Open `/ecs/zendesk-sme-finder-frontend`
3. View the latest log stream

### ECS Service Status

Check service health:

```bash
aws ecs describe-services \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --services $(terraform output -raw ecs_service_name)
```

### Load Balancer Health

Check target health:

```bash
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names zendesk-sme-finder-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)
```

---

## Auto-Scaling Configuration

### CPU-Based Scaling

- **Target**: 70% CPU utilization
- **Scale Out**: Add task when CPU > 70% for 1 minute
- **Scale In**: Remove task when CPU < 70% for 5 minutes

### Memory-Based Scaling

- **Target**: 80% memory utilization
- **Scale Out**: Add task when memory > 80% for 1 minute
- **Scale In**: Remove task when memory < 80% for 5 minutes

### Limits

- **Minimum**: 1 task (always at least one running)
- **Maximum**: 4 tasks (prevents runaway costs)

---

## Troubleshooting

### ECS Service Won't Start

**Symptom**: Service shows "PENDING" or fails to start

**Common Causes**:

1. **No Docker image in ECR**
   ```bash
   # Check if image exists
   aws ecr describe-images --repository-name zendesk-sme-finder-frontend

   # If empty, build and push
   cd terraform
   ./build-and-push-frontend.sh
   ```

2. **Task Definition Issue**
   ```bash
   # Check task definition
   aws ecs describe-task-definition \
     --task-definition zendesk-sme-finder-frontend

   # Look for configuration errors
   ```

3. **IAM Permissions**
   - Verify ECS task execution role has ECR pull permissions
   - Check CloudWatch logs permissions

### Load Balancer Returns 503

**Symptom**: ALB returns "Service Unavailable"

**Solutions**:

1. Check if ECS tasks are running:
   ```bash
   aws ecs list-tasks \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --service-name $(terraform output -raw ecs_service_name)
   ```

2. Check target health:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn <TARGET_GROUP_ARN>
   ```

3. Check security groups:
   - ALB security group allows inbound port 80
   - ECS security group allows inbound port 8501 from ALB

### Application Not Loading

**Symptom**: Browser shows connection error or timeout

**Solutions**:

1. Verify ALB DNS resolves:
   ```bash
   nslookup $(terraform output -raw frontend_url | sed 's|http://||')
   ```

2. Check ECS task logs:
   ```bash
   aws logs tail /ecs/zendesk-sme-finder-frontend --follow
   ```

3. Test health check endpoint:
   ```bash
   # Get ALB DNS
   ALB_DNS=$(terraform output -raw frontend_url | sed 's|http://||')

   # Test health check (from within VPC or if publicly accessible)
   curl http://$ALB_DNS/_stcore/health
   ```

### High Costs

**Symptom**: Unexpected AWS charges

**Solutions**:

1. Check running task count:
   ```bash
   aws ecs describe-services \
     --cluster $(terraform output -raw ecs_cluster_name) \
     --services $(terraform output -raw ecs_service_name) \
     --query 'services[0].runningCount'
   ```

2. Reduce auto-scaling limits:
   - Edit `terraform/variables.tf`
   - Set `ecs_max_capacity = 2`
   - Run `terraform apply`

3. Use FARGATE_SPOT for non-production:
   - Edit `terraform/ecs.tf`
   - Change capacity provider to `FARGATE_SPOT`

---

## Cost Estimation

### Monthly Costs (us-east-1)

**ECS Fargate**:
- 1 task running 24/7: ~$15/month
  - CPU: 0.5 vCPU × $0.04048/hour × 730 hours = $14.78
  - Memory: 1 GB × $0.004445/hour × 730 hours = $3.24
  - **Total**: ~$18/month

**Application Load Balancer**:
- ALB hours: $0.0225/hour × 730 hours = $16.43
- LCU (minimal traffic): ~$5/month
- **Total**: ~$21/month

**NAT Gateway** (2 AZs):
- Gateway hours: 2 × $0.045/hour × 730 hours = $65.70
- Data processing (minimal): ~$5/month
- **Total**: ~$71/month

**ECR Storage**:
- Docker images: <$1/month

**CloudWatch Logs**:
- Ingestion and storage: ~$2/month

**Total Estimated Cost**: ~$113/month for full ECS deployment

**Cost Optimization**:
- Use single NAT Gateway: Save ~$35/month
- Use FARGATE_SPOT: Save ~30% on compute
- Reduce to 0.25 vCPU: Save ~$7/month

---

## Cleanup

To remove all ECS resources:

```bash
cd terraform
terraform destroy
```

This will delete:
- ECS cluster and service
- Load balancer and target groups
- VPC, subnets, and NAT gateways
- ECR repository and images
- All CloudWatch log groups

**Note**: You may need to manually delete:
- ECR images (if repository deletion fails)
- Elastic IPs (if not automatically released)

---

## Comparison: ECS vs EC2

| Feature | ECS Fargate | EC2 (Manual) |
|---------|-------------|--------------|
| Setup Time | 5 minutes | 20 minutes |
| Auto-Scaling | Built-in | Manual setup |
| High Availability | Automatic | Manual setup |
| Patching | AWS managed | Manual |
| Cost (low traffic) | ~$113/month | ~$15/month |
| Cost (high traffic) | Scales automatically | Fixed |
| Load Balancer | Included | Manual setup |

**When to use ECS**:
- Production deployments
- Need high availability
- Auto-scaling required
- Team lacks DevOps expertise

**When to use EC2**:
- Development/testing
- Very low traffic
- Cost-sensitive projects
- Single instance sufficient

---

## Next Steps

1. **Configure Custom Domain** (optional):
   - Register domain in Route 53
   - Create HTTPS certificate in ACM
   - Update ALB to use HTTPS
   - Point domain to ALB

2. **Set up CI/CD**:
   - Use AWS CodePipeline
   - Automate build and deployment
   - Trigger on git push

3. **Enable Container Insights**:
   - Already enabled in ECS cluster
   - View metrics in CloudWatch

4. **Configure Alarms**:
   - High CPU utilization
   - Unhealthy targets
   - High error rates

---

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [ECR User Guide](https://docs.aws.amazon.com/ecr/)
- [Application Load Balancer Guide](https://docs.aws.amazon.com/elasticloadbalancing/)
