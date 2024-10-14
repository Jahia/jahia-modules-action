import * as core from '@actions/core'
import * as github from '@actions/github'
const { execSync } = require('child_process');


async function run(): Promise<void> {
  try {
    const checkName = core.getInput('check_name')
    const pullRequest = github.context.payload.pull_request
    const commit = core.getInput('commit')
    const summary = core.getInput('summary')
    const head_sha =
      commit || (pullRequest && pullRequest.head.sha) || github.context.sha    

    const token =
      core.getInput('token') ||
      core.getInput('github_token') ||
      process.env.GITHUB_TOKEN;

    if (!token) {
      core.setFailed('❌ A token is required to execute this action')
      return
    }

    const instanceId = execSync('ec2metadata --instance-id');    
    const instanceType = execSync('ec2metadata --instance-type');
    core.notice(`Job is running on instance: ${instanceId} (spec: ${instanceType}) - Connect to the instance using: #> aws ssm start-session --target ${instanceId}`)

    core.startGroup(`📘 Keep a session open for Debugging`)
    core.info('Step 1: Log')
    core.endGroup()

    core.startGroup(`📘 AWS SSM (System Manager) Installation instructions`)
    core.info('(once) Step 1: Install the AWS CLI')
    core.info('_____________ Follow the instructions here: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html')
    core.info('_____________ In Short (macOS):')
    core.info('_____________ #> curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"')
    core.info('_____________ #> sudo installer -pkg AWSCLIV2.pkg -target /')
    core.info('_____________ #> aws --version')
    core.info('(once) Step 2: Configure the AWS CLI with your credentials and the region of your instance')
    core.info('those information can be found in your aws account, the region of your instance is not necessarily')
    core.info('where you currently are (for testing we often use the region Ireland : eu-west-1')
    core.info('_____________ #> aws configure')
    core.info('(once) Step 3: Install Session Manager plugin on your machine, python 2.7 is required for this part')
    core.info('_____________ Instructions are available here: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html')
    core.info('_____________ In Short (macOS):')
    core.info('_____________ #> curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"')
    core.info('_____________ #> unzip sessionmanager-bundle.zip ')
    core.info('_____________ #> sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin')
    core.info('ssss')
    core.endGroup()

    core.startGroup(`📘 How to use "SSH" into a runner`)
    core.info('Step 1: Connect using the AWS CLI')
    core.info('_____________ INSTANCE_ID: AWS EC2 Instance ID, displayed at the top of this job, or via the EC2 console')
    core.info('_____________ #> aws ssm start-session --target INSTANCE_ID')
    core.info('Step 2: Access the containers')
    core.info('_____________ #> sudo su')
    core.info('_____________ #> docker ps')
    core.endGroup()

    core.startGroup(`📘 How to use Portforward to access Jahia UI`)
    core.info('Step 1: Establish the tunnel')
    core.info('_____________ Replace the VARIABLE below')
    core.info('_____________ INSTANCE_ID: AWS EC2 Instance ID, displayed at the top of this job, or via the EC2 console')
    core.info('_____________ REMOTE_PORT: TCP Port to bind to on the EC2 Instance (for example: 8080)')
    core.info('_____________ LOCAL_PORT: TCP Port to use on your local machine')
    core.info('_____________ #> aws ssm start-session --target INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters \'{"portNumber":["REMOTE_PORT"],"localPortNumber":["LOCAL_PORT"]}\'')
    core.info('_____________ For Example: ')
    core.info('_____________ #> aws ssm start-session --target INSTANCE_ID --document-name AWS-StartPortForwardingSession --parameters \'{"portNumber":["8080"],"localPortNumber":["8080"]}\'')
    core.endGroup()

    core.startGroup(`📘 Keep a session open for Debugging`)
    core.info('By default, the server will be terminated at the end of execution.')
    core.info('To prevent the session for terminating, simply SSH into the server and create a "/tmp/debug" file')
    core.info('Step 1: SSH into the instance')
    core.info('_____________ #> aws ssm start-session --target INSTANCE_ID')
    core.info('Step 2: Create the debug file')
    core.info('_____________ #> touch /tmp/debug')
    core.info('The session will stay open until it hits the timeout (default to 2 hours)')
    core.info('Step 3: Once done, remove the file')
    core.info('_____________ #> rm /tmp/debug')
    core.endGroup()

    core.startGroup(`📘 Access Docker logs`)
    core.info('By default, the server will stream all the Docker containers logs to CloudWatch')
    core.info('This is useful to debug issues to debug when a runner loses connectivity to GitHub Actions (thus cannot download artifacts)')
    core.info('Note that retention is only 3 days')
    core.info('Step 1: Install awscli')
    core.info('_____________ #> brew install awscli ')    
    core.info('Step 2: Download the log file (you might need to adjust the start time depending on when your instance was started)')
    core.info(`_____________ #> awslogs get /github-self-hosted-runners/ephe5170/docker-logs ${instanceId}/docker-logs --start='4h ago' -G -S  > /tmp/${instanceId}.log`)
    core.info('Step 3: Analyze the logs')
    core.info(`_____________ #> cat /tmp/${instanceId}.log`)
    core.endGroup()

    core.startGroup(`📘 Access Host metrics (NMON)`)
    core.info('The host running the GitHub Actions runners is recording and streaming metrics to CloudWatch using nmon')
    core.info('You can visualize those using awslogs and NMON')
    core.info('Note that retention is only 3 days')
    core.info('Step 1: Download NMON Visualizer and install awscli')
    core.info('_____________ #> curl -L https://github.com/nmonvisualizer/nmonvisualizer/releases/download/2024-02-29/NMONVisualizer_2024-02-29.jar > /tmp/NMONVisualizer.jar')
    core.info('_____________ #> brew install awscli ')
    core.info('Step 2: Download the log file (you might need to adjust the start time depending on when your instance was started)')
    core.info(`_____________ #> awslogs get /github-self-hosted-runners/ephe5170/nmon ${instanceId}/nmon --start='4h ago' -G -S  > /tmp/${instanceId}.nmon`)
    core.info('Step 3: Visualize the data with NMON Visualizer')
    core.info(`_____________ #> java -jar /tmp/NMONVisualizer.jar /tmp/${instanceId}.nmon`)
    core.endGroup()
  } catch (error) {
    if (error instanceof Error) core.setFailed(error.message)
  }
}

run()
