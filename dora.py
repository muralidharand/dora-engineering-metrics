from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

class DORAMetricsCalculator:
    def __init__(self, organization_url, personal_access_token):
        """Initialize connection to Azure DevOps"""
        credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
    
    def get_repository_id(self, project_name, repository_name):
        """Get repository ID for the specified project and repository"""
        git_client = self.connection.clients.get_git_client()
        repositories = git_client.get_repositories(project_name)
        for repo in repositories:
            if repo.name.lower() == repository_name.lower():
                return repo.id
        return None

    def get_deployment_frequency(self, project_name, repository_name, branch_name, start_date, end_date):
        """Calculate deployment frequency for specific branch"""
        builds_client = self.connection.clients.get_build_client()
        
        # Get successful builds for the specific branch
        builds = builds_client.get_builds(
            project=project_name,
            min_time=start_date,
            max_time=end_date,
            status_filter="completed",
            result_filter="succeeded",
            branch_name=f"refs/heads/{branch_name}"
        )
        
        # Count deployments per day
        deploy_dates = [b.finish_time.date() for b in builds]
        deploy_freq = pd.Series(deploy_dates).value_counts().mean() if deploy_dates else 0
        
        return deploy_freq
    
    def get_lead_time_for_changes(self, project_name, repository_name, branch_name, start_date, end_date):
        """Calculate lead time for changes on specific branch"""
        builds_client = self.connection.clients.get_build_client()
        git_client = self.connection.clients.get_git_client()
        
        lead_times = []
        repo_id = self.get_repository_id(project_name, repository_name)
        
        # Get successful builds for the specific branch
        builds = builds_client.get_builds(
            project=project_name,
            min_time=start_date,
            max_time=end_date,
            status_filter="completed",
            result_filter="succeeded",
            branch_name=f"refs/heads/{branch_name}"
        )
        
        for build in builds:
            # Get associated commits
            if repo_id:
                try:
                    # Get commits for this build
                    changes = builds_client.get_build_changes(
                        project=project_name,
                        build_id=build.id
                    )
                    
                    for change in changes:
                        if hasattr(change, 'timestamp'):
                            commit_time = change.timestamp
                            deploy_time = build.finish_time
                            lead_time = (deploy_time - commit_time).total_seconds() / 3600
                            lead_times.append(lead_time)
                except Exception as e:
                    print(f"Error processing build {build.id}: {str(e)}")
                    continue
        
        return np.median(lead_times) if lead_times else 0
    
    def get_change_failure_rate(self, project_name, repository_name, branch_name, start_date, end_date):
        """Calculate change failure rate for specific branch"""
        builds_client = self.connection.clients.get_build_client()
        
        # Get all builds for the specific branch
        builds = builds_client.get_builds(
            project=project_name,
            min_time=start_date,
            max_time=end_date,
            status_filter="completed",
            branch_name=f"refs/heads/{branch_name}"
        )
        
        total_deployments = len(builds)
        failed_deployments = len([b for b in builds if b.result == "failed"])
        
        return (failed_deployments / total_deployments * 100) if total_deployments > 0 else 0
    
    def get_time_to_restore(self, project_name, repository_name, branch_name, start_date, end_date):
        """Calculate time to restore service for specific branch"""
        try:
            work_client = self.connection.clients.get_work_item_tracking_client()
            git_client = self.connection.clients.get_git_client()
            
            from azure.devops.v7_0.work_item_tracking.models import Wiql
            
            # Format dates
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Get repository ID
            repo_id = self.get_repository_id(project_name, repository_name)
            
            # Query for bugs that have been fixed
            wiql_query = f"""
            SELECT [System.Id]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project_name}'
            AND [System.WorkItemType] = 'Bug'
            AND [System.State] = 'Closed'
            AND [System.ChangedDate] >= '{start_str}'
            AND [System.ChangedDate] <= '{end_str}'
            AND [System.Tags] CONTAINS '{branch_name}'
            ORDER BY [System.ChangedDate] DESC
            """
            
            wiql = Wiql(query=wiql_query)
            query_results = work_client.query_by_wiql(wiql).work_items
            
            if not query_results:
                return 0
                
            restoration_times = []
            
            for work_item_ref in query_results:
                work_item = work_client.get_work_item(work_item_ref.id)
                
                if 'System.CreatedDate' in work_item.fields and 'System.ChangedDate' in work_item.fields:
                    created_date = datetime.strptime(work_item.fields['System.CreatedDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    closed_date = datetime.strptime(work_item.fields['System.ChangedDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    
                    restoration_time = (closed_date - created_date).total_seconds() / 3600
                    restoration_times.append(restoration_time)
            
            return np.median(restoration_times) if restoration_times else 0
            
        except Exception as e:
            print(f"Error in get_time_to_restore: {str(e)}")
            return 0
    
    def get_all_metrics(self, project_name, repository_name, branch_name="main", days_back=30):
        """Get all DORA metrics for a specific branch over a time period"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        metrics = {
            'deployment_frequency': self.get_deployment_frequency(
                project_name, repository_name, branch_name, start_date, end_date
            ),
            'lead_time_for_changes': self.get_lead_time_for_changes(
                project_name, repository_name, branch_name, start_date, end_date
            ),
            'change_failure_rate': self.get_change_failure_rate(
                project_name, repository_name, branch_name, start_date, end_date
            ),
            'time_to_restore': self.get_time_to_restore(
                project_name, repository_name, branch_name, start_date, end_date
            )
        }
        
        return metrics

# Example usage
if __name__ == "__main__":
    # Initialize the calculator
    organization_url = input("Enter your Organization url: ")
    personal_access_token = input("Enter your Personal Access Token : ")
    # Configuration
    project_name = input("Enter Project name : ")
    repository_name = input("Enter Repository name : ")
    branch_name = input("Enter Branch name : ")
    days_back = input("Enter number of days to analyze : ")
    days_back = int(days_back)
    
    #Calculate DORA metrics
    calculator = DORAMetricsCalculator(organization_url, personal_access_token)
    
    try:
        # Get metrics
        metrics = calculator.get_all_metrics(
            project_name=project_name,
            repository_name=repository_name,
            branch_name=branch_name,
            days_back=days_back
        )
        
        print(f"\nDORA Metrics for {branch_name} branch in {repository_name}:")
        print(f"Time Period: Last {days_back} days")
        print(f"Deployment Frequency: {metrics['deployment_frequency']:.2f} deployments/day")
        print(f"Lead Time for Changes: {metrics['lead_time_for_changes']:.2f} hours")
        print(f"Change Failure Rate: {metrics['change_failure_rate']:.2f}%")
        print(f"Time to Restore: {metrics['time_to_restore']:.2f} hours")
        
    except Exception as e:
        print(f"Error calculating metrics: {str(e)}")