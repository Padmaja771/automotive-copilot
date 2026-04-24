# Deployment Guide: AWS → Snowflake Event-Driven Pipeline

Follow these steps in order to deploy the production-ready ingestion pipeline.

## 1. Prerequisites
- **AWS CLI** installed and configured (`aws configure`)
- **Terraform** installed
- **Snowflake Account** with `ACCOUNTADMIN` privileges

## 2. Step-by-Step Deployment

### Step A: Initialize Terraform
1. Open a terminal and navigate to the terraform directory:
   ```bash
   cd infrastructure/terraform
   ```
2. Create a `terraform.tfvars` file and add your credentials:
   ```hcl
   snowflake_account  = "BWNONSH-FR57897"
   snowflake_user     = "TESTUSER1236"
   snowflake_password = "YourPassword"
   owner_email        = "your@email.com"
   ```
3. Initialize and apply:
   ```bash
   terraform init
   terraform apply
   ```

### Step B: Create Storage Integration in Snowflake
1. Go to Snowflake and run the code in [`01_storage_integration.sql`](file:///Users/padmaja/Desktop/Padmaja/projects/automotive-copilot/infrastructure/snowflake/01_storage_integration.sql).
2. **Crucial:** After running `DESC INTEGRATION S3_VEHICLE_DOCS_INT;`, copy the two values:
   - `STORAGE_AWS_IAM_USER_ARN`
   - `STORAGE_AWS_EXTERNAL_ID`

### Step C: Update & Apply Terraform
1. Update your `terraform.tfvars` with the two values from Step B:
   ```hcl
   snowflake_iam_user_arn = "arn:aws:iam::..."
   snowflake_external_id  = "..."
   ```
2. Run apply again to finalize the IAM roles:
   ```bash
   terraform apply
   ```

### Step D: Finalize Snowflake Setup
1. Run [`02_ingestion_tables.sql`](file:///Users/padmaja/Desktop/Padmaja/projects/automotive-copilot/infrastructure/snowflake/02_ingestion_tables.sql) to create the tracking tables.
2. Run [`03_external_stage.sql`](file:///Users/padmaja/Desktop/Padmaja/projects/automotive-copilot/infrastructure/snowflake/03_external_stage.sql). Make sure to replace `<s3_bucket_name>` with the output from your terraform apply.
3. Run [`04_automated_parsing_task.sql`](file:///Users/padmaja/Desktop/Padmaja/projects/automotive-copilot/infrastructure/snowflake/04_automated_parsing_task.sql) to set up the AI orchestration.

## 3. Testing the Flow
1. Upload a PDF to your new S3 bucket in the `/incoming` folder.
2. The **AWS Lambda** will fire and insert a row into `PENDING_INGESTION`.
3. Check Snowflake: `SELECT * FROM PENDING_INGESTION;`
4. Wait for the **Snowflake Task** to run (or call the procedure manually: `CALL PROCESS_PENDING_PDFS();`).
5. Your **Streamlit Copilot** will now have new technical data automatically!
