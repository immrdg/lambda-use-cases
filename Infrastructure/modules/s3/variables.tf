variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "dev"
}

variable "force_destroy" {
  description = "A boolean that indicates all objects should be deleted from the bucket on destroy"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
