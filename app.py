"""
Production 990 Lookup Web Application
Optimized for cloud hosting (Heroku, Railway, Render, PythonAnywhere, etc.)
Supports batch and single processing by Name, EIN, or Domain
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import os
import logging
from urllib.parse import urlparse

# Initialize Flask app
app = Flask(__name__, static_folder='.')
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_BASE = "https://projects.propublica.org/nonprofits/api/v2"

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    return jsonify({'status': 'healthy', 'service': '990-lookup'}), 200

@app.route('/api/organization/<ein>')
def get_organization(ein):
    """
    Get organization details by EIN
    Example: /api/organization/530196605
    """
    try:
        ein_clean = ein.replace('-', '').strip()
        logger.info(f"Fetching organization data for EIN: {ein_clean}")
        
        response = requests.get(
            f"{API_BASE}/organizations/{ein_clean}.json",
            timeout=30,
            headers={'User-Agent': 'GoldenVolunteer-990Lookup/1.0'}
        )
        
        if response.status_code == 404:
            logger.warning(f"Organization not found: {ein_clean}")
            return jsonify({'error': 'Organization not found'}), 404
        
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully retrieved data for EIN: {ein_clean}")
        return jsonify(data), 200
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching EIN: {ein_clean}")
        return jsonify({'error': 'Request timeout'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching EIN {ein_clean}: {str(e)}")
        return jsonify({'error': 'Failed to fetch organization data'}), 500
    except Exception as e:
        logger.error(f"Unexpected error for EIN {ein_clean}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search')
def search_organizations():
    """
    Search organizations by name or domain
    Query params: q (query), state (optional state filter)
    Example: /api/search?q=red+cross&state=CA
    """
    try:
        query = request.args.get('q', '').strip()
        state = request.args.get('state', '').strip().upper()
        
        if not query:
            return jsonify({'error': 'Query parameter "q" is required'}), 400
        
        logger.info(f"Searching for: {query}" + (f" in state: {state}" if state else ""))
        
        url = f"{API_BASE}/search.json?q={query}"
        if state:
            url += f"&state[id]={state}"
        
        response = requests.get(
            url,
            timeout=30,
            headers={'User-Agent': 'GoldenVolunteer-990Lookup/1.0'}
        )
        
        response.raise_for_status()
        data = response.json()
        
        result_count = len(data.get('organizations', []))
        logger.info(f"Search returned {result_count} results for: {query}")
        
        return jsonify(data), 200
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout searching for: {query}")
        return jsonify({'error': 'Request timeout'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Error searching for {query}: {str(e)}")
        return jsonify({'error': 'Failed to search organizations'}), 500
    except Exception as e:
        logger.error(f"Unexpected error searching for {query}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search-domain')
def search_by_domain():
    """
    Search organizations by domain
    Query param: domain
    Example: /api/search-domain?domain=redcross.org
    """
    try:
        domain = request.args.get('domain', '').strip()
        
        if not domain:
            return jsonify({'error': 'Query parameter "domain" is required'}), 400
        
        # Extract org name from domain for search
        parsed = urlparse(domain if '://' in domain else f'http://{domain}')
        domain_parts = parsed.netloc.split('.')
        search_term = domain_parts[0] if domain_parts else domain
        
        logger.info(f"Searching by domain: {domain} (using term: {search_term})")
        
        url = f"{API_BASE}/search.json?q={search_term}"
        response = requests.get(
            url,
            timeout=30,
            headers={'User-Agent': 'GoldenVolunteer-990Lookup/1.0'}
        )
        
        response.raise_for_status()
        data = response.json()
        
        return jsonify(data), 200
        
    except Exception as e:
        logger.error(f"Error searching by domain {domain}: {str(e)}")
        return jsonify({'error': 'Failed to search by domain'}), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting 990 Lookup Tool on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
