def main(request):
    import json
    projects =  list_projects()

    #table_id = "nais-billing.navbilling.nais_teams"
    table_id = "nais-analyse-prod-2dcc.navbilling.nais_teams"
    update_teams_in_bq(projects, table_id)

    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}


def update_teams_in_bq(projects, table_id):
    # Construct BQ client
    from google.cloud import bigquery
    client = bigquery.Client()

    # Delete and recreate table (trunc workaround)
    schema = [bigquery.SchemaField("team", "STRING", mode="REQUIRED")]
    table = bigquery.Table(table_id, schema=schema)
    truncate_target_table(client, table_id, table)

    # Prep data for insert
    import pandas as pd
    projects = pd.DataFrame(projects)
    projects.columns=['team']

    # Insert rows
    client.insert_rows_from_dataframe(table, projects)

    return True


def list_projects():
    # Initialize resource manager client
    from google.cloud import resource_manager
    client = resource_manager.Client()

    projects = []

    # DEV
    for project in client.list_projects(filter_params={'parent.id': '747183596397'}):
        projects.append(project.name.rsplit('-dev')[0])

    # PROD
    for project in client.list_projects(filter_params={'parent.id': '83150573901'}):
        projects.append(project.name.rsplit('-prod')[0])

    # Vask duplikater og fjern tomme prosjektnavn
    projects = list(set(filter(None,projects)))

    return projects


def truncate_target_table(client, table_id, table):
    from google.api_core.exceptions import AlreadyExists, NotFound

    # Delete table if exists
    try:
        client.delete_table(table_id)
        print(f'{table_id} deleted')
    except NotFound:
        print(f'Table {table_id} not found, not deleted')

    table = client.create_table(table)  # Make an API request.
    print(f'Created table {table.project}.{table.dataset_id}.{table.table_id}')

    return True
