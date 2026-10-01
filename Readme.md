# Serverless URL Shortener on AWS

A serverless web app that turns long URLs into short links and redirects visitors to the original page. This is my first AWS project, built after completing AWS Cloud Practitioner Essentials.

![Architecture diagram](architecture.svg)

## Demo

![App screenshot](app-url.png)
![App screenshot](app.png)

## How it works

1. The user submits a URL on the web page.
2. `POST /shorten` validates the URL, generates a random 6-character code, and saves it in DynamoDB. A conditional write prevents duplicate codes.
3. Opening `/{code}` looks up the original URL and returns an HTTP 302 redirect.

## AWS services used

| Service | Role |
|---|---|
| API Gateway (HTTP API) | Exposes `POST /shorten` and `GET /{code}` |
| Lambda (Python) | Generates codes, stores links, performs redirects |
| DynamoDB | Stores code → long URL (on-demand capacity) |
| IAM | Least-privilege policy: only `PutItem` and `GetItem` on one table |
| CloudWatch Logs | Debugging and monitoring |

![API routes](api-route.png)
*API Gateway routes.*

![DynamoDB items](DynamoDB.png)
*Links stored in the `url-shortner` table.*

## Security and cost

- IAM role scoped to a single DynamoDB table
- Input validation: http/https only, maximum length, empty-code check
- CORS configured for the browser frontend
- AWS Budgets alert set up; serverless services keep idle cost near zero

## Challenges and what I learned

- **IAM `AccessDeniedException`:** the policy's table ARN didn't match my table name. I found it by reading CloudWatch logs and fixed the policy.
- **DynamoDB `ValidationException`:** opening the bare API address sent an empty code to `GetItem`. I added an input check that returns a clean 400 error.
- Frontend debugging: JavaScript displayed as text because it wasn't inside a `<script>` tag.
- <add anything else you learned>

## Project structure

```
url.html                    Frontend
lambda/lambda_function.py   Backend logic
lambda/iam-policy.json      IAM policy (account ID redacted)
images                      Screenshots
```
