provider "aws" {
  alias   = "lab1"
  region  = var.region
  profile = "lab-module1"
}

provider "aws" {
  alias   = "lab2"
  region  = var.region
  profile = "lab-module2"
}
