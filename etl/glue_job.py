"""
AWS Glue ETL Job for Stock Price Data Processing
Converts raw JSON to optimized Parquet format with proper partitioning
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
import boto3

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def init_glue_job():
    """Initialize Glue job context"""
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'source_bucket',
        'target_bucket', 
        'database_name',
        'rds_secret_name',
        'sns_topic_arn'
    ])
    
    sc = SparkContext()
    glueContext = GlueContext(sc)
    spark = glueContext.spark_session
    job = Job(glueContext)
    job.init(args['JOB_NAME'], args)
    
    return glueContext, spark, job, args

def get_rds_credentials(secret_name: str) -> Dict[str, str]:
    """Get RDS credentials from Secrets Manager"""
    try:
        session = boto3.session.Session()
        client = session.client('secretsmanager')
        
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        
        return {
            'host': secret['host'],
            'port': secret['port'],
            'database': secret['dbname'],
            'username': secret['username'],
            'password': secret['password']
        }
    except Exception as e:
        logger.error(f"Failed to get RDS credentials: {e}")
        raise

def read_raw_json_data(spark, source_path: str) -> DataFrame:
    """Read raw JSON data from S3"""
    try:
        logger.info(f"Reading raw JSON data from: {source_path}")
        
        # Check if path exists before processing
        s3_client = boto3.client('s3')
        bucket = source_path.replace("s3://", "").split("/")[0]
        prefix = "/".join(source_path.replace("s3://", "").split("/")[1:])
        
        try:
            response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if response.get('KeyCount', 0) == 0:
                logger.warning(f"No files found in {source_path}")
                return spark.createDataFrame([], schema=StructType([]))
        except Exception as e:
            logger.error(f"Error checking S3 path: {e}")
            raise
        
        # Define schema for OHLCV data
        candle_schema = ArrayType(
            StructType([
                StructField("timestamp", LongType(), True),
                StructField("open", DoubleType(), True),
                StructField("high", DoubleType(), True), 
                StructField("low", DoubleType(), True),
                StructField("close", DoubleType(), True),
                StructField("volume", LongType(), True)
            ])
        )
        
        symbol_data_schema = StructType([
            StructField("symbol", StringType(), True),
            StructField("resolution", StringType(), True),
            StructField("candles", candle_schema, True),
            StructField("timestamp", StringType(), True),
            StructField("metadata", MapType(StringType(), StringType()), True)
        ])
        
        raw_schema = StructType([
            StructField("data", MapType(StringType(), symbol_data_schema), True),
            StructField("metadata", MapType(StringType(), StringType()), True)
        ])
        
        # Read JSON files
        df = spark.read.option("multiline", "true").schema(raw_schema).json(source_path)
        logger.info(f"Successfully read {df.count()} records from raw data")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to read raw JSON data: {e}")
        raise

def transform_ohlcv_data(df: DataFrame) -> DataFrame:
    """Transform raw JSON to normalized OHLCV format"""
    try:
        logger.info("Starting OHLCV data transformation")
        
        # Explode the data map to get individual symbol data
        symbol_df = df.select(
            explode(col("data")).alias("symbol_key", "symbol_data"),
            col("metadata").alias("ingestion_metadata")
        )
        
        # Extract symbol information
        symbol_expanded = symbol_df.select(
            col("symbol_data.symbol").alias("symbol"),
            col("symbol_data.resolution").alias("resolution"),
            col("symbol_data.candles").alias("candles"),
            col("symbol_data.timestamp").alias("fetch_timestamp"),
            col("ingestion_metadata")
        )
        
        # Explode candles array to get individual OHLCV records
        ohlcv_df = symbol_expanded.select(
            col("symbol"),
            col("resolution"),
            col("fetch_timestamp"),
            explode(col("candles")).alias("candle_data")
        )
        
        # Extract OHLCV values from the array
        final_df = ohlcv_df.select(
            col("symbol"),
            col("resolution"),
            col("candle_data")[0].alias("timestamp_unix"),
            col("candle_data")[1].alias("open"),
            col("candle_data")[2].alias("high"),
            col("candle_data")[3].alias("low"),
            col("candle_data")[4].alias("close"),
            col("candle_data")[5].alias("volume"),
            col("fetch_timestamp")
        )
        
        # Convert Unix timestamp to datetime and add partitioning columns
        transformed_df = final_df.withColumn(
            "timestamp", from_unixtime(col("timestamp_unix")).cast("timestamp")
        ).withColumn(
            "year", year(col("timestamp"))
        ).withColumn(
            "month", month(col("timestamp"))
        ).withColumn(
            "day", dayofmonth(col("timestamp"))
        ).withColumn(
            "hour", hour(col("timestamp"))
        ).withColumn(
            "symbol_clean", regexp_replace(col("symbol"), "NSE:|\\-EQ", "")
        ).withColumn(
            "ingested_at", current_timestamp()
        ).drop("timestamp_unix")
        
        # Add data quality checks
        quality_df = transformed_df.filter(
            col("open").isNotNull() & 
            col("high").isNotNull() & 
            col("low").isNotNull() & 
            col("close").isNotNull() & 
            col("volume").isNotNull() &
            (col("high") >= col("low")) &
            (col("volume") >= 0)
        )
        
        logger.info(f"Transformation completed. Records after quality checks: {quality_df.count()}")
        return quality_df
        
    except Exception as e:
        logger.error(f"Failed to transform OHLCV data: {e}")
        raise

def write_parquet_data(df: DataFrame, target_path: str, resolution: str):
    """Write transformed data to Parquet format with optimized partitioning and compression"""
    try:
        logger.info(f"Writing Parquet data to: {target_path}")
        
        # Optimize DataFrame before writing
        optimized_df = df \
            .coalesce(4) \
            .cache()  # Cache for better performance during partitioning
        
        # Write with optimized Parquet configuration
        optimized_df.write \
            .mode("append") \
            .option("compression", "snappy") \
            .option("parquet.block.size", "134217728") \
            .option("parquet.page.size", "1048576") \
            .option("parquet.enable.dictionary", "true") \
            .option("spark.sql.parquet.compression.codec", "snappy") \
            .option("spark.sql.adaptive.enabled", "true") \
            .option("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .partitionBy("year", "month", "day", "symbol_clean") \
            .parquet(target_path)
        
        # Unpersist cache to free memory
        optimized_df.unpersist()
        
        logger.info("Successfully written optimized Parquet data with enhanced compression")
        
    except Exception as e:
        logger.error(f"Failed to write Parquet data: {e}")
        raise

def insert_metadata_to_rds(df: DataFrame, rds_credentials: Dict[str, str], 
                          target_path: str, resolution: str):
    """Insert processing metadata to RDS"""
    try:
        logger.info("Inserting metadata to RDS")
        
        # Calculate metadata
        total_records = df.count()
        symbols_processed = df.select("symbol_clean").distinct().count()
        processing_timestamp = datetime.utcnow()
        
        # Estimate file size (rough calculation)
        estimated_size_mb = total_records * 0.1  # Rough estimate: 100 bytes per record
        
        # Create JDBC URL
        jdbc_url = f"jdbc:postgresql://{rds_credentials['host']}:{rds_credentials['port']}/{rds_credentials['database']}"
        
        # Metadata DataFrame
        metadata_data = [(
            target_path,
            total_records,
            int(estimated_size_mb * 1024 * 1024),  # Size in bytes
            processing_timestamp.isoformat(),
            resolution,
            symbols_processed
        )]
        
        metadata_schema = StructType([
            StructField("s3_path", StringType(), True),
            StructField("row_count", LongType(), True), 
            StructField("file_size_bytes", LongType(), True),
            StructField("ingested_at", StringType(), True),
            StructField("resolution", StringType(), True),
            StructField("symbols_count", LongType(), True)
        ])
        
        spark = df.sparkSession
        metadata_df = spark.createDataFrame(metadata_data, metadata_schema)
        
        # Write to RDS
        metadata_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "public.ohlcv_metadata") \
            .option("user", rds_credentials['username']) \
            .option("password", rds_credentials['password']) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
        
        logger.info("Successfully inserted metadata to RDS")
        
    except Exception as e:
        logger.error(f"Failed to insert metadata to RDS: {e}")
        raise

def send_completion_notification(sns_topic_arn: str, success: bool, 
                               stats: Dict[str, int], error_msg: str = None):
    """Send SNS notification about job completion"""
    try:
        sns_client = boto3.client('sns')
        
        if success:
            subject = "Glue ETL Job - Success"
            message = f"""
ETL processing completed successfully.

Statistics:
- Total records processed: {stats.get('total_records', 0)}
- Symbols processed: {stats.get('symbols_count', 0)}
- Processing time: {datetime.utcnow().isoformat()}
- Resolution: {stats.get('resolution', 'N/A')}
            """
        else:
            subject = "Glue ETL Job - FAILURE"
            message = f"""
ETL processing failed at {datetime.utcnow().isoformat()}

Error: {error_msg}
            """
        
        sns_client.publish(
            TopicArn=sns_topic_arn,
            Subject=subject,
            Message=message.strip()
        )
        
        logger.info("SNS notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}")

def main():
    """Main ETL workflow"""
    glueContext, spark, job, args = init_glue_job()
    
    try:
        logger.info("Starting Glue ETL job for OHLCV data processing")
        
        # Get job parameters
        source_bucket = args['source_bucket']
        target_bucket = args['target_bucket']
        database_name = args['database_name']
        rds_secret_name = args['rds_secret_name']
        sns_topic_arn = args['sns_topic_arn']
        
        # Process data from the last day
        yesterday = datetime.now() - timedelta(days=1)
        year = yesterday.strftime('%Y')
        month = yesterday.strftime('%m') 
        day = yesterday.strftime('%d')
        
        source_path = f"s3://{source_bucket}/raw/yyyy={year}/mm={month}/dd={day}/"
        target_path = f"s3://{target_bucket}/parquet/resolution=5/"
        
        # Get RDS credentials
        rds_credentials = get_rds_credentials(rds_secret_name)
        
        # Read raw data
        raw_df = read_raw_json_data(spark, source_path)
        
        # Transform data
        transformed_df = transform_ohlcv_data(raw_df)
        
        # Write Parquet data
        write_parquet_data(transformed_df, target_path, "5")
        
        # Insert metadata
        insert_metadata_to_rds(transformed_df, rds_credentials, target_path, "5")
        
        # Calculate statistics
        stats = {
            'total_records': transformed_df.count(),
            'symbols_count': transformed_df.select("symbol_clean").distinct().count(),
            'resolution': '5'
        }
        
        logger.info(f"ETL job completed successfully: {stats}")
        
        # Send success notification
        send_completion_notification(sns_topic_arn, True, stats)
        
        job.commit()
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ETL job failed: {error_msg}")
        
        # Send failure notification
        send_completion_notification(args.get('sns_topic_arn'), False, {}, error_msg)
        
        job.commit()
        raise

if __name__ == "__main__":
    main()