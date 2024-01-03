# Steps:
# 1. Read findings from SEMGREP using API and write to JSON
# 2. Convert the json file to pandas dataframe
# 3. Get the list of all column names from headers 
# 4. list of columns of interest to include in the report
# 5. Create a new dataframe with the columns of interest
# 6. Write the dataframe to excel file
# 7. Create a HTML report from the dataframe
 
import getopt
import requests
import sys
import json
import re
import os
import pandas as pd
from pandas import json_normalize
from datetime import datetime
import logging
import json
from fpdf import FPDF
import html
import pdfkit
 
try:
    SEMGREP_API_WEB_TOKEN = os.environ["SEMGREP_API_WEB_TOKEN"]
except KeyError:
    SEMGREP_API_WEB_TOKEN = "Token not available!"
 
FILTER_IMPORTANT_FINDINGS = False
 
def get_deployments():
    headers = {"Accept": "application/json", "Authorization": "Bearer " + SEMGREP_API_WEB_TOKEN}
 
    r = requests.get('https://semgrep.dev/api/v1/deployments',headers=headers)
    if r.status_code != 200:
        sys.exit(f'Getting org details failed: {r.text}')
    data = json.loads(r.text)
    slug_name = data['deployments'][0].get('slug')
    logging.info("Accessing org: " + slug_name)
    return slug_name
 
def get_projects(slug_name, my_repo):
    logging.info("Getting list of projects in org: " + slug_name)
 
    headers = {"Accept": "application/json", "Authorization": "Bearer " + SEMGREP_API_WEB_TOKEN}
    did_not_find_my_project = True
    r = requests.get('https://semgrep.dev/api/v1/deployments/' + slug_name + '/projects?page=0',headers=headers)
    if r.status_code != 200:
        sys.exit(f'Getting list of projects failed: {r.text}')
 
    data = json.loads(r.text)
    for project in data['projects']:
        project_name = project['name']
        logging.debug("Currently processing project/repo: " + project_name)
        if (project_name == my_repo):
            logging.info("Getting findings for requested project/repo: " + project_name)
            get_findings_per_repo(slug_name, project_name)
     
    if (did_not_find_my_project):
        logging.error("findings for your project: " + my_repo + "not found or the repo has not been scanned yet")
 
def get_findings_per_repo(slug_name, repo):
       
    headers = {"Accept": "application/json", "Authorization": "Bearer " + SEMGREP_API_WEB_TOKEN}
    params =  {"page_size": 2000, "repos": repo}
    # r = requests.get('https://semgrep.dev/api/v1/deployments/' + slug_name + '/findings?repos='+repo,params=params, headers=headers)
    r = requests.get('https://semgrep.dev/api/v1/deployments/' + slug_name + '/findings',params=params, headers=headers)
    if r.status_code != 200:
        sys.exit(f'Getting findings for project failed: {r.text}')
    data = json.loads(r.text)
    file_path = re.sub(r"[^\w\s]", "_", repo) + ".json"
    # file_path = "findings.json"
    if FILTER_IMPORTANT_FINDINGS == True:
        logging.info("Filtering Important findings for requested project/repo: " + project_name)
        data = [obj for obj in data['findings'] if obj["severity"] == "high" and obj["confidence"] == "high" or obj["confidence"] == "medium"]
    else:
        logging.info("All findings for requested project/repo: " + repo)
        data = [obj for obj in data['findings'] ]
 
    with open(file_path, "w") as file:
         json.dump(data, file)
         logging.info("Findings for requested project/repo: " + repo + "written to: " + file_path)
 
def combine_json_files(folder_path, output_file):
    combined_data = []
     
    # Loop through each file in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            print("Opening " + filename)
            with open(os.path.join(folder_path, filename), 'r') as file:
                data = json.load(file)
                 
                # Append data from current file to combined data
                if isinstance(data, list):
                    combined_data.extend(data)
                else:
                    combined_data.append(data)
 
    # Write combined data to output file
    with open(output_file, 'w') as outfile:
        json.dump(combined_data, outfile, indent=4)
 
def json_to_df(json_file):
    # Read the JSON file into a DataFrame
    df = pd.read_json(json_file)
 
    df = df.rename(columns={'rule_name' : 'Finding Title' , 'rule_message'  : 'Finding Description & Remediation', 'relevant_since' : 'First Seen'})
 
 
    # filter out only specific columns
    df = df.loc[:, [ 'Finding Title', 'Finding Description & Remediation', 'state', 'First Seen', 'severity', 'confidence',  'triage_state', 'triaged_at', 'triage_comment', 'state_updated_at', 'repository',  'location' ]]
    # df = df.loc[:, [ 'state', 'repository', 'first_seen_scan_id', 'triage_state', 'severity', 'confidence', 'relevant_since', 'rule_name', 'rule_message', 'location',    'triaged_at', 'triage_comment', 'state_updated_at']]
    # 'state', 'repository', 'first_seen_scan_id', 'triage_state', 'severity', 'confidence', 'relevant_since', 'rule_name', 'rule_message', 'location', 'triaged_at', 'triage_comment', 'state_updated_at'
    # update column to datetime format
    # df['first_seen_scan_id'] = pd.to_datetime(df['first_seen_scan_id'], format='%H-%M--%d-%b-%Y')
 
    logging.info("Findings converted to DF from JSON file : " + json_file)
 
    return df
 
def json_to_df_html(json_file):
    with open(json_file) as json_file_data:
        data = json.load(json_file_data)
        logging.debug(data)
 
    # df = pd.DataFrame(data['results'])
    df = json_normalize(data)
 
    return df
 
def json_to_csv_pandas(json_file, csv_file):
 
    df = json_to_df(json_file)
     
    df = df.rename(columns={'rule_name' : 'Finding Title' , 'rule_message'  : 'Finding Description & Remediation', 'relevant_since' : 'First Seen'})
 
    # Write the DataFrame to CSV
    df.to_csv(csv_file, index=False)
 
    logging.info("Findings converted from JSON file : " + json_file + " to CSV File: " + csv_file)
 
def json_to_xlsx_pandas(json_file, xlsx_file):
 
    df = json_to_df(json_file)
 
    # Write the DataFrame to CSV
    # df.to_excel(xlsx_file, index=False)
 
    writer = pd.ExcelWriter(xlsx_file, engine='xlsxwriter', datetime_format="mmm d yyyy hh:mm")
    df.to_excel(writer, sheet_name='Findings', index=False)
 
    for column in df:
        column_width = max(df[column].astype(str).map(len).max(), len(column))
        col_idx = df.columns.get_loc(column)
        writer.sheets['Findings'].set_column(col_idx, col_idx, column_width)
 
    col_idx = df.columns.get_loc('Finding Title')
    writer.sheets['Findings'].set_column(col_idx, col_idx, 50)
     
    col_idx = df.columns.get_loc('Finding Description & Remediation')
    writer.sheets['Findings'].set_column(col_idx, col_idx, 150)
     
    col_idx = df.columns.get_loc('repository')
    writer.sheets['Findings'].set_column(col_idx, col_idx, 100)
     
    col_idx = df.columns.get_loc('location')
    writer.sheets['Findings'].set_column(col_idx, col_idx, 100)
 
    workbook = writer.book
    worksheet = writer.sheets['Findings']
 
    cell_format = workbook.add_format()
    cell_format.set_text_wrap()
 
    worksheet.set_column('A:A', 50, cell_format)
    worksheet.set_column('B:B', 100, cell_format)
    worksheet.set_column('K:L', 100, cell_format)
 
    cell_format_datetime = workbook.add_format()
    cell_format_datetime.set_num_format('dd/mm/yyyy hh:mm AM/PM')
    worksheet.set_column('D:D', 30, cell_format_datetime)
 
    # # Add some cell formats.
    # datatime_format = workbook.add_format({'datetime_format': 'mmm d yyyy hh:mm'})
 
     
     
    # # Set the column width and format.
    # worksheet.set_column(4, 4, 30, datatime_format)
     
    writer.close()
 
    logging.info("Findings converted from JSON file : " + json_file + " to XLSX File: " + xlsx_file)
 
def generate_html_sast(df_high: pd.DataFrame, df_med: pd.DataFrame, df_low: pd.DataFrame, repo_name):
    # get the Overview table HTML from the dataframe
    # overview_table_html = df_overview.to_html(table_id="table")
    # get the Findings table HTML from the dataframe
    high_findings_table_html = df_high.to_html(index=False, table_id="tableHigh", render_links=True, escape=False, classes='my_table')
    med_findings_table_html = df_med.to_html(index=False, table_id="tableMedium", render_links=True, escape=False, classes='my_table')
    low_findings_table_html = df_low.to_html(index=False, table_id="tableLow", render_links=True, escape=False, classes='my_table')
 
    # Get the current date and time
    now = datetime.now()
 
    # Format the date and time
    formatted_now = now.strftime("%Y-%m-%d %H:%M")
 
    # Print the formatted date and time
    print("Current date and time:", formatted_now)
 
    html = f"""
    <html>
    <head>
    <title> Semgrep SAST Scan Report for Repository: {repo_name} </title>
    <style>
    .my_table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .my_table th, .my_table td {{
        border: 1px solid black;
        text-align: left;
        padding: 8px;
    }}
    .my_table th {{
        background-color: #f2f2f2;
    }}
    /* Example of setting specific column widths */
    .my_table td:nth-of-type(1) {{ /* Targeting first column */
        width: 20% !important;
    }}
    .my_table td:nth-of-type(2) {{ /* Targeting second column */
        width: 30% !important;
    }}
    .my_table td:nth-of-type(3) {{ /* Targeting third column */
        width: 10% !important;
    }}
    .my_table td:nth-of-type(4) {{ /* Targeting fourth column */
        width: 10% !important;
    }}
    .my_table td:nth-of-type(5) {{ /* Targeting fifth column */
        width: 15% !important;
    }}
    .my_table td:nth-of-type(6) {{ /* Targeting sixth column */
        width: 15% !important;
    }}
    </style>
    <style>
        #myImage {{
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 75%; /* or any desired width */
            height: auto; /* to maintain the aspect ratio */
        }}
    </style>
    <style>
        .centered-table {{
            margin-left: auto;
            margin-right: auto;
        }}
    </style>
    <style>
        table {{
            border-collapse: collapse;
            width: 50%;
        }}
        th, td {{
            border: 1px solid black;
            text-align: left;
            padding: 8px;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
    </style>
 
    </head>
    <header>
        <link href="https://cdn.datatables.net/1.11.5/css/jquery.dataTables.min.css" rel="stylesheet">
    </header>
    <body>
    <div style="height: 75px;"></div> <!-- Creates 75px of vertical space -->
    <div class="container">
    <img src="https://i.ibb.co/8xyV6WJ/Semgrep-logo.png" alt="logo" id="myImage">
    </div>
    <div class="container">
    <h1> <p style="text-align: center;" id="sast"> Semgrep SAST Scan Report for Repository: {repo_name} </p> </h1>
    <h2> <p style="text-align: center;" id="reporttime"> Report Generated at {formatted_now} </p> </h2>
    </div>
    <div style="height: 40px;"></div> <!-- Creates 50px of vertical space -->
    <div class="topnav">
    <h2> <p style="text-align: center;" id="sast-summary"> SAST Scan Summary </p> </h2>
 
    <table border="1" class="centered-table"> <!-- Added border for visibility -->
        <!-- Table Header -->
        <tr>
            <th>Vulnerability Severity</th>
            <th>Vulnerability Count</th>
        </tr>
 
        <!-- Table Rows and Data Cells -->
        <tr>
            <td><a href="#sast-high"> Findings- SAST High Severity </a> </td>
            <td> {len(df_high)} </td>
        </tr>
        <tr>
            <td> <a href="#sast-med"> Findings- SAST Medium Severity </a> </td>
            <td> {len(df_med)} </td>
        </tr>
        <tr>
            <td> <a href="#sast-low"> Findings- SAST Low Severity </a> </td>
            <td> {len(df_low)} </td>
        </tr>
    </table>
 
    </div>
 
    <div style="page-break-after: always;"></div>
 
    <div class="heading">
    <h2> <p id="sast-high"> Findings Summary- HIGH Severity </p> </h2>
    </div>
    <div class="container">
        {high_findings_table_html}
    </div>
 
    <div style="page-break-after: always;"></div>
 
    <div class="heading">
    <h2> <p id="sast-med"> Findings Summary- MEDIUM Severity </p> </h2>
    </div>
    <div class="container">
    <table style="width: 100%;">
    {med_findings_table_html}
    </table>
    </div>
 
    <div style="page-break-after: always;"></div>
 
    <div class="heading">
    <h2> <p id="sast-low"> Findings Summary- LOW Severity </p> </h2>
    </div>
    <div class="container">
    <table style="width: 100%;">
    {low_findings_table_html}
    </table>
    </div>
 
    </body>
    </html>
    """
    # return the html
    return html
 
def add_short_ref(row):
    match = re.search(r'\b\w+$', row['ref'])
    # Return the found word or None if no match
    return match.group(0) if match else None
 
def add_short_rule_name(row):
    # Split the string by period
    items = row['Finding Title'].split('.')
    last_item = items[-1]
    link_to_rule = f"https://semgrep.dev/r?q={row['Finding Title']}"
 
    # return the last item
    return (html.unescape("<a href='" + link_to_rule + "'>" + last_item + "</a>"))
 
def add_hyperlink_to_code(row):
    return row['repository.url'] + '/blob/' + row['short_ref'] + '/' + row['location.file_path'] + '#L' + str(row['location.line'])
 
def add_repo_details(row):
    return (html.unescape("<a href='" + row['repository.url'] + "'>" + row['repository.name'] + "</a>"))
 
def add_location_details_hyperlink(row):
    return (html.unescape("<a href='" + row['link_to_code'] + "'>" + row['location.file_path'] + '#L' + str(row['location.line']) + "</a>"))
 
def process_sast_findings(df: pd.DataFrame, html_filename, pdf_filename, repo_name):
    # Create new DF with SAST findings only
    # df_sast = df.loc[(df['check_id'].str.contains('ssc')==False)]
 
    # Get the list of all column names from headers
    column_headers = list(df.columns.values)
    # logging.debug("The Column Header :", column_headers)
 
    # # list of columns of interest to include in the report
    # 'state', 'first_seen_scan_id', 'triage_state', 'severity', 'confidence', 'First Seen', 'Finding Title',
    # 'Finding Description & Remediation', 'triaged_at', 'triage_comment', 'state_updated_at', 'categories',
    # 'repository.name', 'repository.url', 'location.file_path', 'location.line', 'location.column', 'location.end_line', 'location.end_column', 'sourcing_policy.id', 'sourcing_policy.name', 'sourcing_policy.slug'],
    interesting_columns_sast = [
        # 'First Seen',
        'Finding Title',
        'Finding Description & Remediation',
        'severity',
        'state',
        'repository.name',
        'repository.url',
        'location.file_path',
        'location.line',
        'ref',
        # 'finding_hyperlink',
        # 'extra.severity',
        # 'extra.metadata.confidence',
        # 'extra.metadata.semgrep.url',
        # 'extra.metadata.likelihood',
        # 'extra.metadata.impact',
        # 'extra.metadata.owasp',
        # 'extra.metadata.cwe',
        # 'extra.metadata.cwe2021-top25',
        # 'extra.metadata.cwe2022-top25',
    ]
 
    START_ROW = 0
    df_red = df[interesting_columns_sast]
    # df_red = df
 
    # # replace severity values ERROR = HIGH, WARNING = MEDIUM, INFO = LOW
    # df_red = df_red.replace('ERROR', 'HIGH', regex=True)
    # df_red = df_red.replace('WARNING', 'MEDIUM', regex=True)
    # df_red = df_red.replace('INFO', 'LOW', regex=True)
 
    # Apply the function and create a new column
    df_red['Finding Title'] = df_red.apply(add_short_rule_name, axis=1)
    df_red['short_ref'] = df_red.apply(add_short_ref, axis=1)
    df_red['link_to_code'] = df_red.apply(add_hyperlink_to_code, axis=1)
    # df_red['repository'] = df_red.apply(add_repo_details, axis=1)
    df_red['location'] = df_red.apply(add_location_details_hyperlink, axis=1)
 
    df_red.drop(['repository.name', 'repository.url', 'location.file_path', 'location.line', 'link_to_code', 'short_ref'], axis=1, inplace=True)
 
    # create filename for XLSX report
    dir_name = os.path.basename(os.getcwd())
    logging.debug(dir_name)
    current_time = datetime.now().strftime("%Y%m%d-%H%M")
    reportname = f"semgrep_sast_findings_{dir_name}_{current_time}"
    xlsx_filename = f"{reportname}.xlsx"
 
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter(xlsx_filename, engine="xlsxwriter")
 
    # Write the dataframe data to XlsxWriter. Turn off the default header and
    # index and skip one row to allow us to insert a user defined header.
    df_red.to_excel(writer, sheet_name="findings", startrow=START_ROW, header=True, index=False)
 
    # Get the xlsxwriter workbook and worksheet objects.
    workbook = writer.book
    worksheet = writer.sheets["findings"]
 
    # Get the dimensions of the dataframe.
    (max_row, max_col) = df_red.shape
 
    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column.split(".")[-1]} for column in df_red.columns]
 
    # Add the Excel table structure. Pandas will add the data.
    # we start from row = 4 to allow us to insert a title and summary of findings
    worksheet.add_table(START_ROW, 0, max_row+START_ROW, max_col - 1, {"columns": column_settings})
 
    # Add a format.
    text_format = workbook.add_format({'text_wrap' : True})
 
    # Make the text columns width = 48 & add text wrap for clarity
    worksheet.set_column(0, max_col - 1, 48, text_format)
 
    # Make the message columns width = 96 & add text wrap for clarity
    worksheet.set_column(1, 1, 96, text_format)
 
    # Make the severity, confidence, likelyhood & impact columns width = 12
    worksheet.set_column(4, 7, 12)
 
    # #  create new df_high by filtering df_red for HIGH severity
    df_high = df_red.loc[(df_red['severity'] == 'high')]
    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column.split(".")[-1]} for column in df_high.columns]
 
    # #  create new df_med by filtering df_red for MED severity
    df_med = df_red.loc[(df_red['severity'] == 'medium')]
    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column.split(".")[-1]} for column in df_med.columns]
 
    # #  create new df_low by filtering df_red for LOW severity
    df_low = df_red.loc[(df_red['severity'] == 'low')]
    # Create a list of column headers, to use in add_table().
    column_settings = [{"header": column.split(".")[-1]} for column in df_low.columns]
 
    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
 
    # generate the HTML from the dataframe
    html = generate_html_sast(df_high, df_med, df_low, repo_name)
     
    # create filename for HTML report
    # html_filename = f"{reportname}.html"
 
    # write the HTML content to an HTML file
    open(html_filename, "w").write(html)
 
    # convert from HTML to PDF
    options = {
        'orientation': 'Landscape'
    }
    pdfkit.from_string(html, pdf_filename, options=options)
 
def json_to_html_pandas(json_file, html_file, pdf_file, repo_name):
 
    df = json_to_df_html(json_file)
    # logging.debug("data in JSON file is: ")
    # logging.debug(data)
 
    df = df.rename(columns={'rule_name' : 'Finding Title' , 'rule_message'  : 'Finding Description & Remediation', 'relevant_since' : 'First Seen'})
 
    # Write the DataFrame to HTML
    process_sast_findings(df, html_file, pdf_file, repo_name)
 
    logging.info("Findings converted from JSON file : " + json_file + " to HTML File: " + html_file)
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
 
    user_inputs = sys.argv[1:]
    logging.debug(user_inputs)
 
    # get option and value pair from getopt
    try:
        opts, args = getopt.getopt(user_inputs, "r:h", ["repo=", "help"])
        #lets's check out how getopt parse the arguments
        logging.debug(opts)
        logging.debug(args)
    except getopt.GetoptError:
        logging.debug('pass the arguments like -r <name of repo> -h <help> or --repo <name of repo> and --help <help>')
        sys.exit(2)
 
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            logging.info('pass the arguments like -r <name of repo> -h <help> or --repo <name of repo> and --help <help>')
            sys.exit()
        elif opt in ("-r", "--repo"):
            logging.debug(opt)
            logging.debug(arg)
            my_repo = arg
 
    slug_name = get_deployments()
    get_projects(slug_name, my_repo)
    # logging.debug ("starting process to combine JSON files")
    # combine_json_files('.', 'combined.json')
    # logging.debug ("completed combine process")
    logging.info ("starting process to convert JSON file to csv & xlsx")
    output_name = re.sub(r"[^\w\s]", "_", my_repo)
    logging.debug ("output_name: " + output_name)
    json_file = output_name + ".json"
    csv_file = output_name + ".csv"
    xlsx_file = output_name + ".xlsx"
    html_file = output_name + ".html"
    pdf_file = output_name + ".pdf"
 
    json_to_csv_pandas(json_file, csv_file)
    json_to_xlsx_pandas(json_file, xlsx_file)
    # convert_json_to_pdf(json_file)
    json_to_html_pandas(json_file, html_file, pdf_file, my_repo)
     
    logging.info ("completed conversion process")
