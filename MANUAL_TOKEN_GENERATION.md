# Manual Token Generation Guide

## Overview

While your system has automatic token management, you may need to generate tokens manually in these situations:

1. **Initial Setup** - First time configuration
2. **Refresh Token Expiry** - Every ~15 days, refresh tokens expire
3. **Authentication Issues** - When automatic refresh fails
4. **System Recovery** - After major configuration changes

## 🚀 Quick Start (3 Steps)

### Prerequisites
```bash
# Install required Python packages
pip install requests boto3

# Set environment variables (optional)
export FYERS_CLIENT_ID="your-client-id"
export FYERS_APP_SECRET="your-app-secret" 
export AWS_PROFILE="default"
export AWS_REGION="ap-south-1"
```

### Step 1: Generate Authorization URL
```bash
cd "d:\Price Feed Parser\scripts"
python manual_token_generator.py --step 1
```

**Output:**
```
🔗 https://api-t2.fyers.in/api/v3/generate-authcode?client_id=...

📖 Instructions:
1. Click the URL above (or copy-paste it in your browser)
2. Login to your Fyers account  
3. After successful login, you'll be redirected to a URL
4. Copy the 'auth_code' parameter from the redirect URL
```

### Step 2: Extract Auth Code & Generate Tokens
After login, you'll be redirected to a URL like:
```
https://trade.fyers.in/api-login/redirect-to-app?auth_code=XXXXXXXXXXXXXXX&state=sample_state
```

Copy the `auth_code` value and run:
```bash
python manual_token_generator.py --step 2 --auth-code XXXXXXXXXXXXXXX
```

**Output:**
```
✅ Tokens generated successfully!
🔐 Access Token: eyJ0eXAiOiJKV1Qi...
🔄 Refresh Token: eyJhbGciOiJIUzI1...
💾 Tokens saved to: fyers_tokens.json
```

### Step 3: Update AWS SSM Parameters
```bash
python manual_token_generator.py --step 3 --access-token "YOUR_ACCESS_TOKEN" --refresh-token "YOUR_REFRESH_TOKEN"
```

**Output:**
```
✅ Access token updated
✅ Refresh token updated  
✅ Client ID updated
🎉 All SSM parameters updated successfully!
✅ Token validation successful!
🚀 Your system is ready to run automatically!
```

## 🔄 Quick Refresh (When You Have Valid Refresh Token)

If you already have a valid refresh token in SSM:
```bash
python manual_token_generator.py --refresh
```

This will:
1. Get refresh token from SSM
2. Generate new access token
3. Update SSM with new access token
4. Test token validity

## 📋 Manual Method (Without Script)

### Option 1: Browser-Based Token Generation

1. **Build Authorization URL:**
```
https://api-t2.fyers.in/api/v3/generate-authcode?client_id=YOUR_CLIENT_ID&redirect_uri=https://trade.fyers.in/api-login/redirect-to-app&response_type=code&state=sample_state
```

2. **Login and Get Auth Code:**
   - Open URL in browser
   - Login to Fyers
   - Copy `auth_code` from redirect URL

3. **Generate Tokens (cURL):**
```bash
# Calculate app hash first
APP_HASH=$(echo -n "YOUR_CLIENT_ID:YOUR_APP_SECRET" | shasum -a 256 | cut -d' ' -f1)

# Get tokens
curl -X POST "https://api-t2.fyers.in/api/v3/validate-authcode" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "appIdHash": "'$APP_HASH'",
    "code": "YOUR_AUTH_CODE"
  }'
```

4. **Update SSM Parameters:**
```bash
aws ssm put-parameter \
  --name "/stock-pipeline/fyers/access_token" \
  --value "YOUR_ACCESS_TOKEN" \
  --type "SecureString" \
  --overwrite

aws ssm put-parameter \
  --name "/stock-pipeline/fyers/refresh_token" \
  --value "YOUR_REFRESH_TOKEN" \
  --type "SecureString" \
  --overwrite
```

### Option 2: Using Postman/REST Client

**Step 1: Authorization Request**
```
GET https://api-t2.fyers.in/api/v3/generate-authcode
?client_id=YOUR_CLIENT_ID
&redirect_uri=https://trade.fyers.in/api-login/redirect-to-app
&response_type=code
&state=sample_state
```

**Step 2: Token Request**
```
POST https://api-t2.fyers.in/api/v3/validate-authcode
Content-Type: application/json

{
  "grant_type": "authorization_code",
  "appIdHash": "CALCULATED_HASH",
  "code": "AUTH_CODE_FROM_STEP1"
}
```

## 🛠️ Troubleshooting

### Issue: "Invalid client_id"
**Solution:** Verify your Fyers app registration and client ID

### Issue: "Invalid auth_code"
**Solution:** 
- Auth codes expire quickly (~10 minutes)
- Generate new auth code and try again
- Ensure no extra characters when copying

### Issue: "Invalid app hash"
**Solution:**
```bash
# Verify hash calculation
echo -n "CLIENT_ID:APP_SECRET" | shasum -a 256
```

### Issue: "SSM parameter access denied"
**Solution:** Check AWS credentials and IAM permissions:
```bash
aws sts get-caller-identity
aws ssm describe-parameters --filters "Key=Name,Values=/stock-pipeline/fyers/"
```

### Issue: "Token validation failed"
**Solution:**
- Check if tokens were copied correctly
- Verify client ID matches the app
- Test with a simple API call

## 📊 Token Lifecycle Management

### Access Token
- **Validity**: ~24 hours
- **Usage**: All API calls
- **Refresh**: Automatic via Lambda
- **Manual Refresh**: Use refresh token

### Refresh Token  
- **Validity**: ~15 days
- **Usage**: Generate new access tokens
- **Refresh**: Manual login required
- **Storage**: AWS SSM Parameter Store

### Recommended Schedule
```
Daily:    Automatic (Lambda handles)
Weekly:   Monitor logs for issues
Monthly:  Verify refresh token validity  
15 Days:  Manual refresh token update (if needed)
```

## 🔍 Verification Commands

### Check Current Tokens
```bash
aws ssm get-parameters \
  --names "/stock-pipeline/fyers/access_token" \
    "/stock-pipeline/fyers/refresh_token" \
    "/stock-pipeline/fyers/client_id" \
  --with-decryption
```

### Test Token Validity
```bash
# Test access token
curl -H "Authorization: CLIENT_ID:ACCESS_TOKEN" \
     "https://api-t1.fyers.in/api/v3/profile"

# Should return profile information if valid
```

### Monitor Lambda Logs
```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/stock-pipeline-ingestion" \
  --filter-pattern "token" \
  --start-time $(date -d '1 hour ago' +%s)000
```

## 🚨 Emergency Token Recovery

If your system stops working due to token issues:

### 1. Quick Diagnosis
```bash
# Check last Lambda execution
aws lambda invoke \
  --function-name stock-pipeline-ingestion \
  --payload '{}' \
  response.json

# Check response
cat response.json
```

### 2. Force Token Refresh
```bash
# Delete cached access token (forces refresh)
aws ssm delete-parameter --name "/stock-pipeline/fyers/access_token"

# Trigger Lambda to refresh
aws lambda invoke \
  --function-name stock-pipeline-ingestion \
  --payload '{}' \
  response.json
```

### 3. Full Token Regeneration
If refresh token is also expired:
```bash
# Use manual script
python manual_token_generator.py --step 1
# ... follow the full 3-step process
```

## 📱 Mobile App Method

You can also generate tokens using the Fyers mobile app:

1. **Login to Fyers App**
2. **Go to Profile → API Keys**
3. **Generate New Token**
4. **Copy access and refresh tokens**
5. **Update SSM parameters**

## 🎯 Best Practices

### Security
- Never commit tokens to version control
- Use environment variables for client credentials
- Regularly rotate refresh tokens
- Monitor SSM parameter access

### Automation
- Set up CloudWatch alarms for token failures
- Use SNS notifications for manual intervention alerts
- Keep backup refresh tokens in secure storage

### Monitoring  
- Track token refresh frequency
- Monitor API call success rates
- Set up budget alerts for unexpected costs

## 📞 Support

If you encounter issues:

1. **Check Logs**: CloudWatch logs for Lambda function
2. **Verify Credentials**: Fyers app registration and SSM parameters  
3. **Test API**: Direct API calls to verify token validity
4. **Monitor Alerts**: SNS notifications for system issues

## 🎉 Summary

You now have multiple ways to generate Fyers tokens manually:

1. **Automated Script** (`manual_token_generator.py`) - Recommended
2. **Manual Browser Method** - For understanding the process
3. **cURL/Postman** - For debugging
4. **Emergency Recovery** - When everything fails

The automated script handles the complex parts (hash generation, SSM updates, validation) while giving you full control when needed!
