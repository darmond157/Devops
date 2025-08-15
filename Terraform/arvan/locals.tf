locals {
  chosen_image = try(
    [for image in data.arvan_images.terraform_image.distributions : image
    if image.distro_name == var.chosen_distro_name && image.name == var.chosen_name],
    []
  )

  selected_plan = [for plan in data.arvan_plans.plan_list.plans : plan
  if plan.id == var.chosen_plan_id][0]

  chosen_dedicated_server = try(
    [for ds in data.arvan_dedicated_servers.terraform_dedicated_server.dedicated_servers : ds
    if contains(ds.labels, var.dedicated_server_label)],
    []
  )
}
