# Oracle Cloud Always Free Deployment Guide

This guide walks you through deploying the School SaaS system onto an **Oracle Cloud Always Free Ubuntu VPS**.

---

## Step 1: Create Your Oracle Cloud Account
1. Visit: [https://signup.cloud.oracle.com](https://signup.cloud.oracle.com)
2. Sign up for an **Always Free** account (requires a debit/credit card for $1 temporary verification, which is refunded immediately).
3. Select your Home Region (e.g., Frankfurt, London, Ashburn, or South Africa - Johannesburg if available).

---

## Step 2: Create the Always Free Compute Instance (VM)
1. Go to **Compute** → **Instances** → **Create Instance**.
2. **Name**: `school-saas-server`
3. **Placement / Availability Domain**: Any default.
4. **Image and Shape**:
   - **Image**: Click **Change Image** → Choose **Ubuntu 24.04** or **Ubuntu 22.04 LTS**.
   - **Shape**: Click **Change Shape** → Select **Ampere (ARM)** → `VM.Standard.A1.Flex`.
     - OCPU count: `2` (or up to 4)
     - Memory: `12 GB` (or up to 24 GB)
     *(Always Free allows up to 4 OCPUs and 24 GB RAM running 24/7 at $0 cost!)*
5. **Networking**:
   - Primary VNIC: Create new virtual cloud network (default is fine).
   - Public IPv4 Address: Select **Assign a public IPv4 address**.
6. **Add SSH Keys**:
   - Select **Generate a key pair for me**.
   - Click **Save private key** (save `ssh-key-*.key` safely on your computer; you need this to log in).
7. Click **Create**. Within 1–2 minutes, your instance will be **Running** and will display a **Public IP Address**.

---

## Step 3: Open HTTP (80) & HTTPS (443) Ports in Oracle Cloud Console
Oracle Cloud blocks incoming web traffic by default at the Virtual Cloud Network (VCN) level:
1. On your Instance Details page, click your **Subnet** link (under **Instance Information** → **Primary VNIC**).
2. Click the **Default Security List**.
3. Under **Ingress Rules**, click **Add Ingress Rules**:
   - **Source CIDR**: `0.0.0.0/0`
   - **IP Protocol**: `TCP`
   - **Destination Port Range**: `80,443`
   - **Description**: Allow HTTP and HTTPS
4. Click **Add Ingress Rules**.

---

## Step 4: Connect to Your Server via SSH
From your local Windows terminal (PowerShell):
```powershell
ssh -i "path\to\your-ssh-key.key" ubuntu@<YOUR_SERVER_PUBLIC_IP>
```
*(If Windows gives a permissions error on the key file: right-click key file → Properties → Security → Advanced → Disable inheritance → remove all users except your Windows user account with Full Control).*

---

## Step 5: Run Automated Server Setup
Once logged into your Ubuntu server:
```bash
# Clone or copy your project
git clone <YOUR_GIT_REPO_URL> schoolsaas
cd schoolsaas

# Run the automated server setup script
bash deploy/setup_server.sh
```

---

## Step 6: Configure Environment (.env) & Deploy
1. Create your production `.env` file on the server:
```bash
cp .env.example .env
nano .env
```
Ensure:
- `DEBUG=False`
- `ALLOWED_HOSTS=<YOUR_SERVER_PUBLIC_IP>,your-domain.com`
- `CSRF_TRUSTED_ORIGINS=http://<YOUR_SERVER_PUBLIC_IP>,https://your-domain.com`

2. Run the deployment script:
```bash
bash deploy/deploy.sh
```

---

## Step 7: (Optional) Connect Custom Domain & Free SSL
If you have a domain (e.g. `school.timestentechnologies.co.ke`):
1. In your domain DNS manager (e.g. cPanel Zone Editor or Cloudflare), create an **A Record**:
   - Name: `school` (or `@`)
   - Target / IP: `<YOUR_ORACLE_SERVER_PUBLIC_IP>`
2. On your server, run Certbot for free automatic SSL:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```
Certbot will configure SSL and automatic HTTPS renewal.
