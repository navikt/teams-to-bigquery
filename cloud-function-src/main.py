def main(request):
    import json

    projects = list_projects()

    table_id = "nais-analyse-prod-2dcc.navbilling.nais_teams"
    update_teams_in_bq(projects, table_id)

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


def update_teams_in_bq(projects, table_id):
    # Construct BQ client
    from google.cloud import bigquery
    client = bigquery.Client(project='nais-analyse-prod-2dcc')

    # Delete and recreate table (trunc workaround)
    schema = [bigquery.SchemaField("team", "STRING", mode="REQUIRED")]
    table = bigquery.Table(table_id, schema=schema)
    truncate_target_table(client, table_id, table)

    # Prep data for insert
    import pandas as pd
    projects = pd.DataFrame(projects)
    projects.columns=['team']

    # Insert rows
    try:
        client.insert_rows_from_dataframe(table, projects)
        print(f'Inserted {len(projects)} rows into {table_id}')
    except Exception as e:
        print(e)

    return True


def list_projects():
    # Initialize resource manager client
    from google.cloud import resourcemanager_v3 as grm
    client = grm.ProjectsClient()

    projects = []

    # DEV
    for project in client.list_projects(parent="folders/970894780659"):
        if '-dev' in project.display_name:
            team_name = project.display_name.split('-dev')[0]
        elif '-ci' in project.display_name:
            team_name = project.display_name.split('-ci')[0]
        else:
            team_name = project.display_name
        projects.append(team_name)

    # PROD
    for project in client.list_projects(parent="folders/707911698083"):
        projects.append(project.display_name.rsplit('-prod')[0])

    # Vask duplikater og fjern tomme prosjektnavn
    projects = list(set(filter(None,projects)))

    print(f"Found {len(projects)} projects")

    return projects


def truncate_target_table(client, table_id, table):
    from google.api_core.exceptions import NotFound

    # Truncate table if exists
    try:
        client.query(f'TRUNCATE TABLE `{table_id}`').result()
        print(f'{table_id} truncated')
    except NotFound:
        print(f'Table {table_id} not found, creating it')
        table = client.create_table(table)  # Make an API request.
        print(f'Created table {table.project}.{table.dataset_id}.{table.table_id}')

    return True

if __name__ == "__main__":
    main(None)