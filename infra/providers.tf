terraform {
  required_version = ">= 1.10.0"

  backend "s3" {
    bucket       = "vana-events-tfstate-371425121968"
    key          = "vana-event-tracking-platform/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }

    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}