# Cloudinary Setup for Customer Profile Images

## Overview
This setup ensures customer profile images are properly stored and served in production using Cloudinary cloud storage.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Cloudinary Credentials
1. Go to [https://cloudinary.com](https://cloudinary.com)
2. Sign up for a free account (generous free tier)
3. Go to your Dashboard
4. Copy your credentials:
   - Cloud Name
   - API Key  
   - API Secret

### 3. Set Environment Variables

#### For Development (Local):
Create a `.env` file in your project root:
```bash
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

#### For Production (Server):
Set these environment variables on your server:
```bash
export CLOUDINARY_CLOUD_NAME=your-cloud-name
export CLOUDINARY_API_KEY=your-api-key
export CLOUDINARY_API_SECRET=your-api-secret
```

### 4. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## How It Works

### Development Mode (DEBUG=True)
- Images stored locally in `/media/` folder
- Uses Django's default FileSystemStorage
- Images served from local server

### Production Mode (DEBUG=False)
- Images automatically uploaded to Cloudinary
- Served via Cloudinary's CDN (fast global delivery)
- Automatic image optimization and resizing
- No storage worries on your server

## Features Implemented

### 1. Smart Fallback
- If image fails to load, shows default user icon
- Handles empty/missing images gracefully

### 2. Error Handling
- `onerror` JavaScript fallback for broken images
- Proper template conditionals for missing images

### 3. Optimized Display
- 40px circular profile images in table view
- Responsive sizing for mobile devices
- Proper CSS classes for consistent styling

## Benefits

1. **Production Ready**: No manual file management needed
2. **CDN Delivery**: Fast image loading worldwide
3. **Auto Optimization**: Cloudinary optimizes images automatically
4. **Scalable**: Handles unlimited image uploads
5. **Secure**: Signed URLs and secure delivery
6. **Free Tier**: Generous free usage limits

## Testing

### Upload Test:
1. Go to customer creation/edit form
2. Upload a profile image
3. Verify it appears in customer list table
4. Check that image loads properly

### Fallback Test:
1. Create customer without image
2. Verify default icon appears
3. Test with broken image URL
4. Confirm fallback works

## Production Checklist

- [ ] Cloudinary account created
- [ ] Environment variables set on server
- [ ] `DEBUG=False` in production settings
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Migrations run (`python manage.py migrate`)
- [ ] Test image upload in production
- [ ] Verify images load in customer table

## Support

- Cloudinary Documentation: https://cloudinary.com/documentation
- Django Integration: https://cloudinary.com/documentation/django_integration
- Free tier includes: 25GB storage, 25GB bandwidth/month
