#!/usr/bin/env python3
"""
Production-ready application runner for Eknal Link
"""
import os
import logging
from app import app, create_tables

def setup_logging():
    """Configure logging for production"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

if __name__ == '__main__':
    # Setup logging
    setup_logging()
    
    # Create database tables
    create_tables()
    
    # Get configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    if not debug:
        logging.info("Starting Eknal Link in production mode")
    
    app.run(
        host=host,
        port=port,
        debug=debug
    )