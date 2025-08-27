
module "postgres_vector" {
  source = "./modules/postgres-vector"  # Path to your module
  
  resource_group_name = "rg-k8s-ai-agent-dev"
  location           = "East US"
  project_name       = "k8s-ai-agent"
  environment        = "dev"
  admin_username     = "pgadmin"
  admin_password     = var.postgres_password
  
  # Add your public IP to allow connections
  allowed_ip_addresses = [
    "YOUR_PUBLIC_IP",  # Get this from: curl ifconfig.me
  ]
}

# Variables
variable "postgres_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

# Outputs
output "postgres_connection_string" {
  value     = module.postgres_vector.connection_string
  sensitive = true
}

