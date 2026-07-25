variable "volume_name" {
  description = "Name tag for the EBS volume"
  type        = string
}

variable "availability_zone" {
  description = "AZ to create the volume in"
  type        = string
  default     = "us-east-1a"
}

variable "size" {
  description = "Volume size in GiB"
  type        = number
  default     = 1
}

variable "volume_type" {
  description = "EBS volume type"
  type        = string
  default     = "gp3"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "tags" {
  description = "Additional resource tags"
  type        = map(string)
  default     = {}
}
