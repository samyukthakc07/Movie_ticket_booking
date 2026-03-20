# Oracle Cloud Always Free Deployment

This project is a good fit for an Oracle Cloud Always Free Ubuntu VM because the app needs:

- a web process
- a background worker process
- a link that stays up for more than a short trial window

Oracle documents that Always Free resources are available for the life of the account, which makes it a better fit than short-lived free tiers for evaluation hosting.

## Recommended setup

- OS: `Ubuntu 24.04`
- Shape: `Always Free` VM
- Public IP: reserve one so the link does not change if the VM restarts
- Open inbound ports: `22`, `80`

## Before you start

1. Commit and push your latest project changes to GitHub.
2. Decide whether you want:
   - your exact current local data copied to the VM, or
   - a fresh demo database generated on the VM

If you deploy from Git alone, your local `db.sqlite3` will not be included because it is ignored by Git.

## 1. Create the VM in Oracle Cloud

From the Oracle Cloud console:

1. Create a compute instance.
2. Choose `Ubuntu 24.04`.
3. Choose an `Always Free` shape.
4. Assign or reserve a public IP.
5. Add ingress rules for port `22` and port `80`.
6. Download the SSH private key if Oracle generates one for you.

## 2. Connect to the VM

```bash
ssh -i /path/to/your-key ubuntu@YOUR_VM_PUBLIC_IP
```

## 3. Install system packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx git build-essential libpq-dev pkg-config default-libmysqlclient-dev
```

`default-libmysqlclient-dev` is included because `requirements.txt` contains `mysqlclient`, which often needs native build dependencies on Ubuntu.

## 4. Upload the code

Option A: clone from GitHub

```bash
cd /home/ubuntu
git clone <your-repo-url> movie_booking_system
cd movie_booking_system
```

Option B: copy your whole local project folder to the VM

Use this if you want the VM to include your current local `db.sqlite3` exactly as it is.

## 5. Create the virtual environment

```bash
cd /home/ubuntu/movie_booking_system
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp deploy/oracle/env.example .env
```

## 6. Configure environment variables

Edit `.env`:

```bash
nano /home/ubuntu/movie_booking_system/.env
```

Set these values:

- `DJANGO_SECRET_KEY` to a long random value
- `DJANGO_ALLOWED_HOSTS=YOUR_VM_PUBLIC_IP`
- `DJANGO_CSRF_TRUSTED_ORIGINS=http://YOUR_VM_PUBLIC_IP`
- `DJANGO_SECURE_SSL_REDIRECT=False`

Important:

- `DJANGO_SECURE_SSL_REDIRECT=False` is required for the initial IP-based HTTP deployment in this guide.
- If you later add a real domain and HTTPS, change `DJANGO_CSRF_TRUSTED_ORIGINS` to your HTTPS domain and set `DJANGO_SECURE_SSL_REDIRECT=True`.

## 7. Prepare the database

Load the environment first:

```bash
cd /home/ubuntu/movie_booking_system
. .venv/bin/activate
set -a
. ./.env
set +a
```

### Option A: use your existing local data

From your local machine, copy your database file to the server:

```bash
scp -i /path/to/your-key db.sqlite3 ubuntu@YOUR_VM_PUBLIC_IP:/home/ubuntu/movie_booking_system/db.sqlite3
```

Then run:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### Option B: create fresh demo data on the VM

```bash
python manage.py migrate
python manage.py generate_movies
python populate_demo.py
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 8. Install and start system services

```bash
sudo cp deploy/oracle/movie-booking-web.service /etc/systemd/system/
sudo cp deploy/oracle/movie-booking-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable movie-booking-web
sudo systemctl enable movie-booking-worker
sudo systemctl start movie-booking-web
sudo systemctl start movie-booking-worker
sudo systemctl status movie-booking-web
sudo systemctl status movie-booking-worker
```

The worker service is important for:

- expiring seat locks
- processing queued booking emails

## 9. Configure Nginx

```bash
sudo cp deploy/oracle/nginx-movie-booking.conf /etc/nginx/sites-available/movie-booking
sudo ln -s /etc/nginx/sites-available/movie-booking /etc/nginx/sites-enabled/movie-booking
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 10. Verify the deployment

Open:

```text
http://YOUR_VM_PUBLIC_IP
```

If it does not load, check:

```bash
sudo systemctl status movie-booking-web
sudo systemctl status movie-booking-worker
sudo systemctl status nginx
journalctl -u movie-booking-web -n 100 --no-pager
journalctl -u movie-booking-worker -n 100 --no-pager
```

## Updating after code changes

```bash
cd /home/ubuntu/movie_booking_system
git pull
. .venv/bin/activate
pip install -r requirements.txt
set -a
. ./.env
set +a
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart movie-booking-web
sudo systemctl restart movie-booking-worker
```

## Final live link

Your live link will be:

```text
http://YOUR_VM_PUBLIC_IP
```

If you reserve the public IP and keep the VM running, that same link should remain valid for your 15-20 day evaluation window.
