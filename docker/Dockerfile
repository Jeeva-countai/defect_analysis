# Use Ubuntu 20.04 as the base image
FROM ubuntu:20.04

# Set environment variables for non-interactive installs and timezone
ENV DEBIAN_FRONTEND=noninteractive TZ=Asia/Kolkata

# Combine all RUN commands into a single layer to minimize image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3 \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    unzip \
    tzdata \
    postgresql \
    postgresql-contrib && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    pip3 install --upgrade pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
RUN apt-get update && apt-get install -y openssh-client
RUN apt-get update && apt-get install -y iputils-ping

# Set up PostgreSQL service to run
RUN service postgresql start

# Copy the requirements.txt file to the container's /install directory
COPY requirements.txt /install/

# Install Python dependencies from requirements.txt
RUN pip3 install -r /install/requirements.txt

RUN mkdir -p /app/files

# Set the working directory inside the container
WORKDIR /app

# Copy all the application files (main.py, client.py, etc.) into the container
COPY . /app

# Unzip or handle specific file extraction if needed
# If you need to unzip files, use the following line:
RUN unzip main.zip

# Expose the port for the app if it's necessary
EXPOSE 9996
# Set the command to run the application
CMD ["python3", "main.py"]
