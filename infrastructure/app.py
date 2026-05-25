"""AWS CDK application entry point."""
import aws_cdk as cdk

from image_pipeline_stack import ImagePipelineStack

app = cdk.App()
ImagePipelineStack(app, "ImagePipelineStack")
app.synth()
