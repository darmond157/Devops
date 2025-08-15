variable "region" {
  type        = string
  description = "The chosen region for resources"
  default     = "ir-thr-fr1"
}

variable "chosen_distro_name" {
  type        = string
  description = "The chosen distro name for image"
  default     = "ubuntu"
}

variable "chosen_name" {
  type        = string
  description = "The chosen release for image"
  default     = "24.04"
}

variable "chosen_plan_id" {
  type        = string
  description = "The chosen ID of plan"
  default     = "eco-1-1-0"
}

variable "chosen_server_group_id" {
  type        = string
  description = "The chosen ID of Server Group"
  default     = ""
}