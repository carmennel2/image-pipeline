# Container image for the worker Lambda function.
# Built on the AWS-provided Python base image for Lambda.
FROM public.ecr.aws/lambda/python:3.12

# Install the worker's Python dependencies.
COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code onto the Lambda task root, which is on the
# Python import path inside the container.
COPY worker/ ${LAMBDA_TASK_ROOT}/worker/
COPY shared/ ${LAMBDA_TASK_ROOT}/shared/

# Run the `handler` function in the worker.handler module.
CMD ["worker.handler.handler"]
