"""
Pipeline Orchestrator Module
=============================
Main entry point for running the Weather Data ETL Pipeline. Coordinates the 
flow of execution from extraction, validation, transformation, to final database loading.
Tracks system-wide performance and writes execution summary logs.
"""

import time
import sys
from src.logger import logger
from src.extract import WeatherExtractor
from src.validate import WeatherValidator
from src.transform import WeatherTransformer
from src.load import WeatherLoader


class WeatherETLPipeline:
    """Orchestrates the entire ETL workflow from end to end."""

    def __init__(self) -> None:
        self.extractor = WeatherExtractor()
        self.validator = WeatherValidator()
        self.transformer = WeatherTransformer()
        self.loader = WeatherLoader()

    def run(self) -> bool:
        """
        Executes the ETL process sequentially.
        
        Returns:
            True if pipeline completed successfully, False otherwise.
        """
        start_time = time.time()
        logger.info("=========================================")
        logger.info("      STARTING WEATHER ETL PIPELINE      ")
        logger.info("=========================================")

        try:
            # 1. EXTRACT STAGE
            logger.info(">>> [STAGE 1] Ingestion: Extracting Raw JSON from OpenWeather...")
            raw_files_saved = self.extractor.extract_all()
            if raw_files_saved == 0:
                logger.warning("No raw data was successfully extracted. Aborting pipeline run.")
                return False

            # 2. VALIDATE STAGE
            logger.info(">>> [STAGE 2] Quality Assurance: Validating Raw Payloads...")
            valid_records = self.validator.validate_raw_files()
            if not valid_records:
                logger.warning("No valid records found after QA validation checking. Aborting pipeline run.")
                return False

            # 3. TRANSFORM STAGE
            logger.info(">>> [STAGE 3] Processing: Transforming Units & Categorizing...")
            processed_df = self.transformer.transform_records(valid_records)
            if processed_df.empty:
                logger.warning("Transformation resulted in an empty dataset. Aborting pipeline run.")
                return False
                
            csv_path = self.transformer.save_to_csv(processed_df)
            if not csv_path:
                logger.warning("Failed to save processed data to CSV. Continuing load step...")

            # 4. LOAD STAGE
            logger.info(">>> [STAGE 4] Storage: Loading Transformed Dataset into Database...")
            inserted, skipped = self.loader.load_dataframe(processed_df)

            # Execution Summary
            elapsed_time = time.time() - start_time
            logger.info("=========================================")
            logger.info("     WEATHER ETL PIPELINE SUCCESS        ")
            logger.info("=========================================")
            logger.info(f"Total Processing Time    : {elapsed_time:.2f} seconds")
            logger.info(f"Cities Configured        : {len(self.extractor.cities)}")
            logger.info(f"Raw Files Written        : {raw_files_saved}")
            logger.info(f"Validated JSONs Accepted : {len(valid_records)}")
            logger.info(f"Database Rows Inserted   : {inserted}")
            logger.info(f"Database Rows Skipped    : {skipped}")
            logger.info("=========================================")
            return True

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.critical("=========================================")
            logger.critical("     WEATHER ETL PIPELINE FAILURE        ")
            logger.critical("=========================================")
            logger.critical(f"Pipeline crashed after {elapsed_time:.2f} seconds.")
            logger.critical(f"Failure Reason: {e}", exc_info=True)
            logger.critical("=========================================")
            return False


if __name__ == "__main__":
    pipeline = WeatherETLPipeline()
    success = pipeline.run()
    if not success:
        sys.exit(1)
