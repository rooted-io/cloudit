import os
import subprocess
import json
from multiprocessing import Pool
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


# Google Cloud Audit
def gcp_audit(gcp_credentials_file):
    if os.path.isfile(gcp_credentials_file):
        with open(gcp_credentials_file, 'r') as file:
            data = json.load(file)
            azure_customers = data.get("customers", [])
            pool = Pool()
            pool.starmap(run_prowler, [(customer, "gcp") for customer in azure_customers])
            pool.close()
            pool.join()
    else:
        print(f"The GCP JSON file '{gcp_credentials_file}' does not exist... please add this file with the Azure credentials")


# Azure Audit
def azure_audit(azure_credentials_file):
    if os.path.isfile(azure_credentials_file):
        with open(azure_credentials_file, 'r') as file:
            data = json.load(file)
            azure_customers = data.get("customers", [])
            pool = Pool()
            pool.starmap(run_prowler, [(customer, "azure") for customer in azure_customers])
            pool.close()
            pool.join()
    else:
        print(f"The Azure JSON file '{azure_credentials_file}' does not exist... please add this file with the Azure credentials")


# AWS Audit
def aws_audit(aws_credentials_file):
    if os.path.isfile(aws_credentials_file):
        with open(aws_credentials_file, 'r') as file:
            data = json.load(file)
            aws_customers = data.get("customers", [])
            pool = Pool()
            pool.starmap(run_prowler, [(customer, "aws") for customer in aws_customers])
            pool.close()
            pool.join()
    else:
        print(f"The AWS JSON file '{aws_credentials_file}' does not exist... please add this file with the AWS credentials")


# Function to run Prowler for a specific customer and cloud
def run_prowler(customer, cloud):
    customer_name = customer.get("customer_name", "")
    date = os.popen("date +'%Y%m%d_%H%M%S'").read().strip()

    if cloud == "gcp":
        google_application_credentials = customer.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        gcp_services = " ".join(customer.get("SERVICES", []))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_application_credentials
        output_file = f"{customer_name}-gcp-posture-{date}"
        prowler_command = f"prowler gcp --services {gcp_services} --severity high critical -q -F {output_file}"

    elif cloud == "aws":
        aws_access_key_id = customer.get("AWS_ACCESS_KEY_ID", "")
        aws_secret_access_key = customer.get("AWS_SECRET_ACCESS_KEY", "")
        aws_regions = " ".join(customer.get("REGIONS", []))
        aws_services = " ".join(customer.get("SERVICES", []))
        os.environ["AWS_ACCESS_KEY_ID"] = aws_access_key_id
        os.environ["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key
        output_file = f"{customer_name}-aws-posture-{date}"
        # prowler_command = f"prowler aws -f {aws_regions} --services {aws_services} -q -F {output_file}"
        prowler_command = f"prowler aws -f {aws_regions} --services {aws_services} --severity high critical -q -F {output_file}"
        # Replace logo in reports
        replace_content_in_html_files("output", cloud_provider='aws')
    elif cloud == "azure":
        azure_client_id = customer.get("AZURE_CLIENT_ID", "")
        azure_services = " ".join(customer.get("SERVICES", []))
        azure_client_secret = customer.get("AZURE_CLIENT_SECRET", "")
        azure_tenant_id = customer.get("AZURE_TENANT_ID", "")
        subscription_ids = " ".join(customer.get("AZURE_SUBSCRIPTION_ID", []))
        os.environ["AZURE_CLIENT_ID"] = azure_client_id
        os.environ["AZURE_CLIENT_SECRET"] = azure_client_secret
        os.environ["AZURE_TENANT_ID"] = azure_tenant_id
        output_file = f"{customer_name}-azure-posture-{date}"
        prowler_command = f"prowler azure --sp-env-auth --subscription-ids {subscription_ids} --services {azure_services} --severity high critical -q -F {output_file}"
        replace_content_in_html_files("output", cloud_provider='azure')

    print(f"DEBUG - running prowler command: {prowler_command}")
    subprocess.run(prowler_command, shell=True)
    os.environ.pop("AWS_ACCESS_KEY_ID", None)
    os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
    os.environ.pop("AZURE_CLIENT_ID", None)
    os.environ.pop("AZURE_CLIENT_SECRET", None)
    os.environ.pop("AZURE_TENANT_ID", None)


# Function to clean old files
def clean_old_files():
    output_folder = "output"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    current_date = datetime.now()
    threshold_date = current_date - timedelta(days=90)

    for filename in os.listdir(output_folder):
        file_path = os.path.join(output_folder, filename)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        if file_mtime < threshold_date:
            os.remove(file_path)

# Function to replace prowler logo and links in the reports


def replace_content_in_html_files(folder_path, cloud_provider):
    search_content = '\n<a href="https://github.com/prowler-cloud/prowler/"><img alt="prowler-logo" class="float-left card-img-left mt-4 mr-4 ml-4" src="https://user-images.githubusercontent.com/3985464/113734260-7ba06900-96fb-11eb-82bc-d4f68a1e2710.png"/></a>\n'
    replace_content = '\n<a href="https://rootedsec.io/"><img alt="rooted-logo" class="float-left card-img-left mt-4 mr-4 ml-4" src="https://rootedsec.io/images/rooted.png" width="300" height="200"/></a>\n'

    # Loop through all HTML files in the folder
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.html') and cloud_provider in file:
                print(f"Replace logo in {cloud_provider} html report")
                file_path = os.path.join(root, file)

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the HTML content with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')

                # Check if the search content is in the parsed HTML
                if search_content in str(soup):
                    # Replace the content
                    new_content = str(soup).replace(search_content, replace_content)

                    # Write the modified content back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)


def main():
    start_time = datetime.now()
    print("##########################  CloudIT Started ☁️ 🔬 ##########################")
    clean_old_files()

    credentials_folder = "credentials"
    aws_credentials_file = f"{credentials_folder}/aws/aws-credentials.json"
    azure_credentials_file = f"{credentials_folder}/azure/azure-credentials.json"
    gcp_credentials_file = f"{credentials_folder}/gcp/gcp-credentials.json"

    # GCP AUDIT
    gcp_audit(gcp_credentials_file)
    replace_content_in_html_files("output", cloud_provider='gcp')

    # AZURE AUDIT
    azure_audit(azure_credentials_file)
    replace_content_in_html_files("output", cloud_provider='azure')

    # AWS AUDIT
    aws_audit(aws_credentials_file)
    replace_content_in_html_files("output", cloud_provider='aws')

    end_time = datetime.now()
    total_execution_time = end_time - start_time
    print(f"############# CloudIT assessment has been completed. Total execution time: {total_execution_time} ############# ")


if __name__ == "__main__":
    main()
