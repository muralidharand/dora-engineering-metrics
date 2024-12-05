# DORA Engineering Metrics


## Installation
Install the required packages and execute the script like below.

```py
pip install azure-core azure-devops pandas numpy python-dateutil requests
```

## Execution
Execute the application like below.

```py
python dora.py
Enter your Organization url: https://dev.azure.com/murali
Enter your Personal Access Token : ****
Enter Project name : Murali.HelloWorld
Enter Repository name : Murali.HelloWorld
Enter Branch name : releases/v1
Enter number of days to analyze : 15
```
The results will be printed like this.

```py
DORA Metrics for releases/v1 branch in Murali.HelloWorld:
Time Period: Last 15 days
Deployment Frequency: 28.20 deployments/day
Lead Time for Changes: 25.53 hours
Change Failure Rate: 1.32%
Time to Restore: 0.00 hours

```
## Reference
[Engineering Metrics](https://blogs.codingfreaks.net/dora-metrics-calculator-for-azure-devops)


