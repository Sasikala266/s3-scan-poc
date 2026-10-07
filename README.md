# Path Finder (S3 Static Website + API Gateway REST + Lambda)

## What it creates
- S3 bucket with static website hosting and public index.html
- Seed folders/prefixes and sample data objects: csv/, json/, xml/, html/
- Lambda function to locate a file by name and return its S3 URI
- API Gateway REST API: POST /prod/scan (CORS enabled)

## 🚀 Quick Start

### Deploy to Your Own AWS Account

Path Finder is designed to be deployed into **your own AWS environment**. The recommended path uses GitHub Actions to run Terraform automatically — no local tooling required beyond the AWS CLI for running audits.

---

### Option A: GitHub Actions (Recommended)

This is the standard open-source workflow. The CI/CD pipeline handles all infrastructure deployment for you.

**1️⃣ Fork the repository**

Click **Fork** at the top-right of this page to create your own copy under your GitHub account. This gives you full control to customize the configuration and deploy to your AWS environment.

**2️⃣ Configure AWS credentials in GitHub Secrets**

Go to your forked repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**, and add:

| Secret name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS access key ID |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret access key |

The IAM user or role these credentials belong to needs permissions to create Lambda functions, API Gateway, IAM roles and policy (standard Terraform deployment permissions).

**3️⃣ Update the Terraform backend (one-time setup)**

Edit `versions.tf` in your fork and replace the S3 backend values with your own:

```hcl
backend "s3" {
  bucket = "your-terraform-state-bucket"   # ← your S3 bucket for Terraform state
  key    = "Path-Finder/terraform.tfstate"
  region = "us-east-1"
}
```

> 💡 If you don't have a Terraform state bucket yet, create one in S3, or remove the `backend "s3"` block entirely to use local state for testing.

**4️⃣ Deploy — push to main**

Commit your `versions.tf` change and push to `main`. The **Terraform Deploy** GitHub Actions workflow triggers automatically and runs:

```
terraform init → terraform validate → terraform plan → terraform apply
```

Track progress under the **Actions** tab of your repo. Deployment typically takes 1–2 minutes.

You can also trigger it manually: **Actions** → **Terraform Deploy** → **Run workflow**.

---

### Option B: Local Deployment

Prefer to run everything from your machine? Install [Terraform ≥ 1.6](https://developer.hashicorp.com/terraform/downloads) and the [AWS CLI](https://aws.amazon.com/cli/), configure your credentials, then:

```bash
# Clone (or fork first, then clone your fork)
git clone https://github.com/Sasikala266/s3-scan-poc.git
cd Path-Finder

# (Optional) switch to local state — edit versions.tf to remove the backend "s3" block
# or update it to point to your own state bucket

terraform init
terraform plan
terraform apply
```

---