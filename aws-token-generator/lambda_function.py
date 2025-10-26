import json
import boto3
import hashlib
import requests
import os
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    """
    AWS Lambda handler for Fyers Token Generator Web UI
    Handles both serving the UI and processing token generation requests
    """
    
    # Set CORS headers for all responses
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    try:
        http_method = event.get('httpMethod', 'GET')
        
        # Handle OPTIONS request for CORS
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Handle GET request - serve the web UI
        if http_method == 'GET':
            return serve_web_ui(headers)
        
        # Handle POST request - process token generation
        if http_method == 'POST':
            return process_token_request(event, headers)
        
        return {
            'statusCode': 405,
            'headers': headers,
            'body': json.dumps({'error': 'Method not allowed'})
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def serve_web_ui(headers):
    """Serve the token generator web UI"""
    
    # Update headers for HTML content
    html_headers = headers.copy()
    html_headers['Content-Type'] = 'text/html'
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔑 AWS Fyers Token Generator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #333;
            font-size: 2.2em;
            margin-bottom: 10px;
        }
        
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        
        .step {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }
        
        .step h3 {
            color: #007bff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .step-number {
            background: #007bff;
            color: white;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: bold;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #007bff;
        }
        
        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            margin: 5px;
        }
        
        .btn:hover {
            background: #0056b3;
        }
        
        .btn-success {
            background: #28a745;
        }
        
        .btn-success:hover {
            background: #1e7e34;
        }
        
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .error-message {
            background: #f8d7da;
            border: 1px solid #f1aeb5;
            color: #721c24;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        
        .token-display {
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            font-family: monospace;
            font-size: 14px;
            max-height: 120px;
            overflow-y: auto;
            word-break: break-all;
        }
        
        .auth-url {
            background: #e7f3ff;
            border: 1px solid #b8daff;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔑 AWS Fyers Token Generator</h1>
            <p>Serverless daily token generation</p>
        </div>

        <div class="step">
            <h3><span class="step-number">1</span>Configure Credentials</h3>
            <div class="form-group">
                <label for="clientId">Fyers Client ID:</label>
                <input type="text" id="clientId" placeholder="ABC123-100">
            </div>
            <div class="form-group">
                <label for="appSecret">Fyers App Secret:</label>
                <input type="password" id="appSecret" placeholder="Your app secret">
            </div>
            <div class="form-group">
                <label for="redirectUri">Redirect URI (from your Fyers app):</label>
                <select id="redirectUri">
                    <option value="https://www.google.com/">https://www.google.com/ (Your App Setting)</option>
                    <option value="custom">Custom (enter below)</option>
                </select>
            </div>
            <div class="form-group" id="customRedirectGroup" style="display: none;">
                <label for="customRedirect">Custom Redirect URI:</label>
                <input type="text" id="customRedirect" placeholder="Enter your custom redirect URI">
            </div>
            <button class="btn" onclick="generateAuthUrl()">Generate Login URL</button>
        </div>

        <div class="step" id="step2" style="display: none;">
            <h3><span class="step-number">2</span>Login to Fyers</h3>
            <div id="authUrlDisplay" class="auth-url"></div>
            <button class="btn btn-success" id="openFyersBtn" onclick="openFyersLogin()" style="display: none;">
                🌐 Open Fyers Login
            </button>
            <div class="form-group" style="margin-top: 15px;">
                <label for="redirectUrl">Paste the redirect URL here:</label>
                <textarea id="redirectUrl" rows="3" placeholder="Redirect URL will appear here after you select redirect URI above"></textarea>
            </div>
            <button class="btn" onclick="generateTokens()">Generate & Store Tokens</button>
        </div>

        <div class="step" id="step3" style="display: none;">
            <h3><span class="step-number">3</span>✅ Success!</h3>
            <div id="tokenResults"></div>
        </div>

        <div id="messages"></div>
    </div>

    <script>
        let authUrl = '';
        const API_BASE = window.location.origin + window.location.pathname;

        // Show/hide custom redirect input
        document.addEventListener('DOMContentLoaded', function() {
            const redirectSelect = document.getElementById('redirectUri');
            const customGroup = document.getElementById('customRedirectGroup');
            
            redirectSelect.addEventListener('change', function() {
                if (this.value === 'custom') {
                    customGroup.style.display = 'block';
                } else {
                    customGroup.style.display = 'none';
                }
            });
        });

        function generateAuthUrl() {
            const clientId = document.getElementById('clientId').value.trim();
            const appSecret = document.getElementById('appSecret').value.trim();
            const redirectSelect = document.getElementById('redirectUri');
            const customRedirect = document.getElementById('customRedirect').value.trim();

            if (!clientId || !appSecret) {
                showMessage('Please enter both Client ID and App Secret', 'error');
                return;
            }

            let redirectUri;
            if (redirectSelect.value === 'custom') {
                if (!customRedirect) {
                    showMessage('Please enter custom redirect URI', 'error');
                    return;
                }
                redirectUri = customRedirect;
            } else {
                redirectUri = redirectSelect.value;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: 'code',
                state: 'sample_state'
            });

            authUrl = `https://api-t1.fyers.in/api/v3/generate-authcode?${params.toString()}`;
            
            document.getElementById('authUrlDisplay').innerHTML = `
                <strong>Authorization URL:</strong><br>
                <code>${authUrl}</code><br><br>
                <strong>Expected Redirect URL format:</strong><br>
                <code>${redirectUri}?auth_code=...</code>
            `;
            
            document.getElementById('openFyersBtn').style.display = 'inline-block';
            document.getElementById('step2').style.display = 'block';
            
            // Update placeholder text
            document.getElementById('redirectUrl').placeholder = `${redirectUri}?auth_code=...`;
            
            showMessage('✅ Authorization URL generated!', 'success');
        }

        function openFyersLogin() {
            if (authUrl) {
                window.open(authUrl, '_blank');
                showMessage('Login opened in new tab. Copy the redirect URL after login.', 'success');
            }
        }

        async function generateTokens() {
            const clientId = document.getElementById('clientId').value.trim();
            const appSecret = document.getElementById('appSecret').value.trim();
            const redirectUrl = document.getElementById('redirectUrl').value.trim();
            
            if (!redirectUrl) {
                showMessage('Please paste the redirect URL', 'error');
                return;
            }

            try {
                showMessage('🔄 Generating and storing tokens...', 'pending');

                const response = await fetch(API_BASE, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        action: 'generate_tokens',
                        client_id: clientId,
                        app_secret: appSecret,
                        redirect_url: redirectUrl
                    })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    document.getElementById('tokenResults').innerHTML = `
                        <div class="success-message">
                            <strong>✅ Tokens stored in AWS SSM!</strong><br>
                            Generated at: ${new Date().toLocaleString()}<br>
                            Your pipeline will now use these tokens automatically.
                        </div>
                        <div class="token-display">
                            <strong>Access Token:</strong> ${data.access_token.substring(0, 50)}...<br>
                            <strong>Stored in:</strong> ${data.parameters_updated.join(', ')}
                        </div>
                    `;
                    
                    document.getElementById('step3').style.display = 'block';
                    showMessage('✅ Tokens successfully stored! Your pipeline is ready.', 'success');
                } else {
                    showMessage(`❌ Error: ${data.error || 'Token generation failed'}`, 'error');
                }
            } catch (error) {
                showMessage(`❌ Error: ${error.message}`, 'error');
            }
        }

        function showMessage(message, type) {
            const messagesDiv = document.getElementById('messages');
            const statusClass = type === 'success' ? 'success-message' : 
                              type === 'error' ? 'error-message' : 
                              'auth-url';
            
            messagesDiv.innerHTML = `<div class="${statusClass}">${message}</div>`;

            if (type === 'success') {
                setTimeout(() => {
                    messagesDiv.innerHTML = '';
                }, 5000);
            }
        }
    </script>
</body>
</html>
    """
    
    return {
        'statusCode': 200,
        'headers': html_headers,
        'body': html_content
    }

def process_token_request(event, headers):
    """Process token generation request"""
    
    try:
        # Parse request body
        if event.get('body'):
            body = json.loads(event['body'])
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Request body is required'})
            }
        
        action = body.get('action')
        
        if action == 'generate_tokens':
            return generate_and_store_tokens(body, headers)
        else:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid action'})
            }
            
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        logger.error(f"Error processing token request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

def generate_and_store_tokens(body, headers):
    """Generate tokens from auth code and store in SSM"""
    
    try:
        client_id = body.get('client_id')
        app_secret = body.get('app_secret')
        redirect_url = body.get('redirect_url')
        
        if not all([client_id, app_secret, redirect_url]):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Extract auth code from redirect URL
        try:
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)
            auth_code = query_params.get('auth_code', [None])[0]
            
            if not auth_code:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Auth code not found in redirect URL'})
                }
                
        except Exception as e:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': f'Invalid redirect URL format: {str(e)}'})
            }
        
        # Generate app hash
        app_hash = hashlib.sha256(f"{client_id}:{app_secret}".encode()).hexdigest()
        
        # Request tokens from Fyers API
        token_payload = {
            'grant_type': 'authorization_code',
            'appIdHash': app_hash,
            'code': auth_code
        }
        
        logger.info("Requesting tokens from Fyers API...")
        response = requests.post(
            'https://api-t1.fyers.in/api/v3/validate-authcode',
            json=token_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        response_data = response.json()
        logger.info(f"Fyers API response status: {response_data.get('s')}")
        
        if response_data.get('s') != 'ok':
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': f"Fyers API error: {response_data.get('message', 'Unknown error')}"
                })
            }
        
        access_token = response_data.get('access_token')
        refresh_token = response_data.get('refresh_token')
        
        if not access_token or not refresh_token:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Tokens not received from Fyers API'})
            }
        
        # Store tokens in SSM Parameter Store
        project_name = os.environ.get('PROJECT_NAME', 'stock-pipeline')

        parameters_updated = []
        
        # Store access token
        access_token_param = f"/{project_name}/fyers/access_token"
        ssm.put_parameter(
            Name=access_token_param,
            Value=access_token,
            Type='SecureString',
            Overwrite=True
        )
        parameters_updated.append(access_token_param)
        
        # Store refresh token
        refresh_token_param = f"/{project_name}/fyers/refresh_token"
        ssm.put_parameter(
            Name=refresh_token_param,
            Value=refresh_token,
            Type='SecureString',
            Overwrite=True
        )
        parameters_updated.append(refresh_token_param)
        
        # Store client ID
        client_id_param = f"/{project_name}/fyers/client_id"
        ssm.put_parameter(
            Name=client_id_param,
            Value=client_id,
            Type='SecureString',
            Overwrite=True
        )
        parameters_updated.append(client_id_param)
        
        # Store app secret
        app_secret_param = f"/{project_name}/fyers/app_secret"
        ssm.put_parameter(
            Name=app_secret_param,
            Value=app_secret,
            Type='SecureString',
            Overwrite=True
        )
        parameters_updated.append(app_secret_param)
        
        logger.info(f"Successfully stored tokens in SSM parameters: {parameters_updated}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': 'Tokens generated and stored successfully',
                'access_token': access_token,
                'parameters_updated': parameters_updated,
                'generated_at': datetime.now().isoformat()
            })
        }
        
    except requests.RequestException as e:
        logger.error(f"Error calling Fyers API: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Fyers API request failed: {str(e)}'})
        }
    except Exception as e:
        logger.error(f"Error generating tokens: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': f'Token generation failed: {str(e)}'})
        }