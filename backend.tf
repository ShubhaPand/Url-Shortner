terraform {
  backend "s3" {
    bucket       = "tfstate-url"
    key          = "url-shortener/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
  }
}