"""AWS CDK application entry point.

Defines the deployable infrastructure for the image-processing pipeline.
See design document Section 11.
"""
import aws_cdk as cdk

from image_pipeline_stack import ImagePipelineStack

app = cdk.App()
ImagePipelineStack(app, "ImagePipelineStack")
app.synth()
