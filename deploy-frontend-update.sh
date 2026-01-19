#!/bin/bash
set -e

echo "=== Zendesk SME Finder - Frontend Update Deployment ==="
echo ""

# Configuration
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/sme-finder-frontend"
CLUSTER_NAME="sme-finder-cluster"
SERVICE_NAME="sme-finder-frontend-service"

echo "Account ID: $ACCOUNT_ID"
echo "ECR Repository: $ECR_REPO"
echo "ECS Cluster: $CLUSTER_NAME"
echo "ECS Service: $SERVICE_NAME"
echo ""

# Step 1: Login to ECR
echo "Step 1: Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo "✓ Logged in to ECR"
echo ""

# Step 2: Build Docker image
echo "Step 2: Building Docker image..."
cd frontend
docker build -t sme-finder-frontend:latest .
echo "✓ Docker image built"
echo ""

# Step 3: Tag image for ECR
echo "Step 3: Tagging image for ECR..."
docker tag sme-finder-frontend:latest ${ECR_REPO}:latest
echo "✓ Image tagged"
echo ""

# Step 4: Push to ECR
echo "Step 4: Pushing image to ECR..."
docker push ${ECR_REPO}:latest
echo "✓ Image pushed to ECR"
echo ""

# Step 5: Force new deployment
echo "Step 5: Forcing new ECS deployment..."
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service ${SERVICE_NAME} \
    --force-new-deployment \
    --region ${AWS_REGION} \
    --output json > /dev/null
echo "✓ Deployment triggered"
echo ""

# Step 6: Wait for deployment to complete
echo "Step 6: Waiting for deployment to complete..."
echo "This may take 3-5 minutes..."
aws ecs wait services-stable \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION}
echo "✓ Deployment completed successfully"
echo ""

# Step 7: Get service status
echo "Step 7: Checking service status..."
SERVICE_STATUS=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services ${SERVICE_NAME} \
    --region ${AWS_REGION} \
    --query 'services[0].{Status:status,DesiredCount:desiredCount,RunningCount:runningCount}' \
    --output json)
echo "$SERVICE_STATUS" | jq .
echo ""

echo "=== Deployment Complete ==="
echo ""
echo "Frontend URL: http://sme-finder-alb-9460206.us-east-1.elb.amazonaws.com/"
echo ""
echo "The chat interface is now live!"
