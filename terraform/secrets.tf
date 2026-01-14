# Zendesk Credentials Secret
resource "aws_secretsmanager_secret" "zendesk_credentials" {
  name        = "${var.project_name}/zendesk-credentials"
  description = "Zendesk API credentials for SME Finder"

  recovery_window_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-zendesk-credentials"
    }
  )
}

resource "aws_secretsmanager_secret_version" "zendesk_credentials" {
  secret_id = aws_secretsmanager_secret.zendesk_credentials.id
  secret_string = jsonencode({
    domain    = var.zendesk_domain
    email     = var.zendesk_email
    api_token = var.zendesk_api_token
  })
}

# Slack Credentials Secret
resource "aws_secretsmanager_secret" "slack_credentials" {
  name        = "${var.project_name}/slack-credentials"
  description = "Slack bot credentials for SME Finder"

  recovery_window_in_days = 7

  tags = merge(
    var.additional_tags,
    {
      Name = "${var.project_name}-slack-credentials"
    }
  )
}

resource "aws_secretsmanager_secret_version" "slack_credentials" {
  secret_id = aws_secretsmanager_secret.slack_credentials.id
  secret_string = jsonencode({
    bot_token = var.slack_bot_token
    team_url  = var.slack_team_url
  })
}

# Outputs
output "zendesk_secret_arn" {
  description = "ARN of the Zendesk credentials secret"
  value       = aws_secretsmanager_secret.zendesk_credentials.arn
  sensitive   = true
}

output "slack_secret_arn" {
  description = "ARN of the Slack credentials secret"
  value       = aws_secretsmanager_secret.slack_credentials.arn
  sensitive   = true
}
