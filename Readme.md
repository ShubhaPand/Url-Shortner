# Serverless URL Shortener on AWS

![Terraform](https://github.com/ShubhaPand/Url-Shortner/actions/workflows/terraform.yml/badge.svg)

**Live demo:** http://url-shortener-frontend-2026.s3-website-us-east-1.amazonaws.com
*(Served over HTTP by S3 website hosting. HTTPS through CloudFront is planned.)*

A serverless web app that turns long URLs into short links and redirects visitors to the original page. This is my first AWS project, built after completing AWS Cloud Practitioner Essentials. I first built it by hand in the console, then rebuilt the whole stack, backend and frontend, with **Terraform** and added a **GitHub Actions CI/CD pipeline** that deploys every change automatically.

![Architecture diagram](architecture.svg)

## Demo

![App screenshot](app-url.png) ![App screenshot](app.png)

<!-- Add your demo video link here, for example: [Watch the demo](https://...) -->

## How it works

1. The user submits a URL on the web page (hosted on S3).
2. `POST /shorten` validates the URL, generates a random 6-character code, and saves it in DynamoDB. A conditional write prevents duplicate codes. The API returns `{"short_code": "..."}`.
3. The page builds the short link from the API address and the code.
4. Opening `/{code}` looks up the original URL and returns an HTTP 302 redirect.

## AWS services and tools used

| Service / Tool         | Role                                                                          |
| ---------------------- | ----------------------------------------------------------------------------- |
| S3 (website hosting)   | Hosts the static frontend (`url.html`)                                        |
| API Gateway (HTTP API) | Exposes `POST /shorten` and `GET /{code}`, with CORS limited to the frontend  |
| Lambda (Python)        | Generates codes, stores links, performs redirects                             |
| DynamoDB               | Stores code → long URL (on-demand capacity)                                   |
| IAM                    | Least-privilege policy: only `PutItem` and `GetItem` on one table             |
| CloudWatch Logs        | Debugging and monitoring                                                      |
| Terraform              | Defines the whole stack as code: DynamoDB, Lambda, API Gateway, S3 frontend   |
| S3 (Terraform state)   | Stores Terraform remote state (versioned bucket with state locking)           |
| GitHub Actions         | CI/CD pipeline: plans on pull requests, applies on merge to `main`            |
| IAM OIDC provider      | Lets GitHub Actions get temporary AWS credentials, with no stored access keys |

![API routes](api-route.png)

*API Gateway routes.*

![DynamoDB items](DynamoDB.png)

*Links stored in the `url-shortner` table.*

## Infrastructure as Code

Everything is defined in Terraform:

- `main.tf`: DynamoDB table, IAM role and policies, Lambda function, API Gateway (routes, integration, stage, CORS) and the Lambda invoke permission
- `frontend.tf`: S3 bucket with website hosting, public-read policy for the site, and the uploaded `url.html`
- `backend.tf`: remote state in S3 with versioning and state locking, so state is shared between my laptop and the pipeline instead of sitting in a local file

To deploy manually:

```
terraform init
terraform plan
terraform apply
```

After an apply, `terraform output` prints the API URL and the website URL.

## CI/CD pipeline

Every change goes through GitHub Actions (`.github/workflows/terraform.yml`):

- **On a pull request:** checks formatting (`terraform fmt`), validates the config, and runs `terraform plan` so I can review exactly what would change.
- **On merge to `main`:** runs `terraform apply` to deploy the change. This includes the frontend, since `url.html` is uploaded to S3 by Terraform.

The pipeline signs in to AWS with **OpenID Connect (OIDC)**. GitHub receives short-lived credentials by assuming an IAM role that trusts only this repository, so there are no long-lived access keys stored in GitHub.

## Security and cost

- IAM role for the Lambda scoped to a single DynamoDB table
- GitHub Actions uses OIDC with a role limited to this repository, with no stored AWS keys
- API CORS allows only the frontend's origin, not every site
- The S3 bucket policy makes only the website bucket publicly readable, and it holds just the frontend page
- Terraform state is stored in a private, versioned S3 bucket; state files are excluded from Git
- Input validation: http/https only, maximum length, empty-code check
- AWS Budgets alert set up; serverless services keep idle cost near zero

## Challenges and what I learned

- **IAM `AccessDeniedException`:** the policy's table ARN didn't match my table name. I found it by reading CloudWatch logs and fixed the policy.
- **DynamoDB `ValidationException`:** opening the bare API address sent an empty code to `GetItem`. I added an input check that returns a clean 400 error.
- **GitHub Actions OIDC login failed with `Not authorized to perform sts:AssumeRoleWithWebIdentity`:** my IAM trust policy looked correct, so I added a debug step to the workflow that decoded the OIDC token. It showed that the `sub` claim included numeric account and repository IDs (`repo:<owner>@<id>/<repo>@<id>:...`), so my trust condition never matched. Updating the condition to the real claim value fixed it.
- **Accidentally committing the `.terraform/` folder:** the push was rejected because the downloaded AWS provider binary exceeded GitHub's 100 MB file limit. I added a `.gitignore`, removed the folder from Git's staging area, and re-committed without it.
- **Terraform plan showed a `source_code_hash` change on the Lambda:** the zip built on the Linux runner hashed differently from the one built on my Windows machine. The change was harmless, and I learned to let the pipeline do the applying.
- **A "CORS error" that wasn't CORS:** the browser blocked the frontend's request, but the CORS settings were correct. Using `curl -i` showed the real response, a 404 from API Gateway, because my Terraform route was `POST /` instead of `POST /shorten`. Without a matching route, API Gateway sends no CORS headers, so the browser reported CORS.
- **A one-character typo caught at apply time:** a stray space in the route key (`POST /shorten`) made API Gateway reject the update with a `BadRequestException`. The pipeline stopped before changing anything, so the live API stayed intact.
- **Frontend and backend disagreed on the response format:** the page looked for `short_url`, while the Terraform-built Lambda returns `short_code`, so every success showed an error. I fixed the page to build the link from the API address and the code.

## Project structure

```
url.html                          Frontend (deployed to S3 by Terraform)
lambda_function.py                Lambda backend logic
lambda/                           Lambda source packaged by Terraform
iam-policy.json                   IAM policy (account ID redacted)
main.tf                           Terraform: DynamoDB, IAM, Lambda, API Gateway
frontend.tf                       Terraform: S3 website hosting for the frontend
backend.tf                        Remote state configuration (S3)
.github/workflows/terraform.yml   CI/CD pipeline
architecture.svg                  Architecture diagram
*.png                             Screenshots
```

## Next steps

- Serve the frontend over HTTPS with CloudFront and make the bucket private
- Build the Lambda zip with Terraform's `archive_file` so plans stay clean
- Add CloudWatch alarms for Lambda errors and API Gateway 5xx responses
- Tighten the pipeline role from managed policies to a custom least-privilege policy