output "events_bucket_name" {
  description = "S3 bucket where raw events are stored"
  value       = aws_s3_bucket.events.bucket
}

output "firehose_stream_name" {
  description = "Kinesis Firehose delivery stream name"
  value       = aws_kinesis_firehose_delivery_stream.events.name
}

output "lambda_function_name" {
  description = "Lambda function that ingests events"
  value       = aws_lambda_function.event_ingestion.function_name
}

output "api_endpoint" {
  description = "HTTP API Gateway endpoint"
  value       = "${aws_apigatewayv2_api.events_api.api_endpoint}/${var.environment}/events"
}

output "failed_events_dlq_url" {
  description = "SQS queue URL used for failed event delivery"
  value       = aws_sqs_queue.failed_events_dlq.url
}