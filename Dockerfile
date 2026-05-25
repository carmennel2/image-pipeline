# Worker Lambda container image, built on the AWS Python base image.
FROM public.ecr.aws/lambda/python:3.12

# Install the Python dependencies.
COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code onto the Lambda task root (on the import path).
COPY worker/ ${LAMBDA_TASK_ROOT}/worker/
COPY shared/ ${LAMBDA_TASK_ROOT}/shared/

# Run the handler function in the worker.handler module.
CMD ["worker.handler.handler"]
