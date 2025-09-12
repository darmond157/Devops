provider "google" {
  region = "us-central1"
}

provider "google" {
  alias  = "europe"
  region = "europe-west1"
}

resource "google_compute_instance" "example" {
  provider = google.europe

  name         = "example-instance"
  machine_type = "n1-standard-1"
  zone         = "europe-west1-b"
  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }
  network_interface {
    network = "default"
    access_config {
      // Ephemeral IP
    }
  }
}



// ------------------------------------------------------------------



provider "google" {
  project = "project-1"
  region  = "us-central1"
}

provider "google-beta" {
  project = "project-1"
  region  = "us-central1"
}

resource "google_compute_instance" "example" {
  provider = google-beta

  name         = "example-instance"
  machine_type = "n1-standard-1"
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  network_interface {
    network = "default"
    access_config {
      // Ephemeral IP
    }
  }
}
