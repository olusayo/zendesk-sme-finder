#!/bin/bash
# Build and Push Frontend Docker Image to ECR
# This script builds the Streamlit frontend and pushes it to Amazon ECR

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Building and Pushing Frontend to ECR${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo -e "${YELLOW}AWS Account ID:${NC} $AWS_ACCOUNT_ID"
echo -e "${YELLOW}AWS Region:${NC} $AWS_REGION"
echo ""

# Get ECR repository URL from Terraform output
echo -e "${YELLOW}Getting ECR repository URL from Terraform...${NC}"
ECR_REPO=$(terraform output -raw ecr_repository_url 2>/dev/null || echo "")

if [ -z "$ECR_REPO" ]; then
    echo -e "${RED}Error: Could not get ECR repository URL from Terraform.${NC}"
    echo -e "${RED}Make sure you have run 'terraform apply' first.${NC}"
    exit 1
fi

echo -e "${YELLOW}ECR Repository:${NC} $ECR_REPO"
echo ""

# Authenticate Docker to ECR
echo -e "${YELLOW}Authenticating Docker to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to authenticate Docker to ECR${NC}"
    exit 1
fi
echo -e "${GREEN}Authentication successful!${NC}"
echo ""

# Navigate to frontend directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FRONTEND_DIR="$SCRIPT_DIR/../frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Error: Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi

cd "$FRONTEND_DIR"
echo -e "${YELLOW}Building Docker image from:${NC} $FRONTEND_DIR"
echo ""

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t zendesk-sme-finder-frontend:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed${NC}"
    exit 1
fi
echo -e "${GREEN}Docker build successful!${NC}"
echo ""

# Tag image for ECR
echo -e "${YELLOW}Tagging image for ECR...${NC}"
docker tag zendesk-sme-finder-frontend:latest $ECR_REPO:latest

# Also tag with timestamp for version history
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker tag zendesk-sme-finder-frontend:latest $ECR_REPO:$TIMESTAMP

echo -e "${GREEN}Image tagged successfully${NC}"
echo ""

# Push to ECR
echo -e "${YELLOW}Pushing image to ECR (this may take a few minutes)...${NC}"
docker push $ECR_REPO:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to push image to ECR${NC}"
    exit 1
fi

echo -e "${YELLOW}Pushing timestamped version...${NC}"
docker push $ECR_REPO:$TIMESTAMP

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Success!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${GREEN}Docker image pushed successfully to ECR:${NC}"
echo -e "  - $ECR_REPO:latest"
echo -e "  - $ECR_REPO:$TIMESTAMP"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. ECS will automatically pull the new image on next deployment"
echo -e "2. To force a new deployment, run:"
echo -e "   ${GREEN}aws ecs update-service --cluster \$(terraform output -raw ecs_cluster_name) --service \$(terraform output -raw ecs_service_name) --force-new-deployment --region $AWS_REGION${NC}"
echo ""
