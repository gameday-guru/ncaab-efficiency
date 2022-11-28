# Title: alpine-august-tiger
# UUID: 0467dd3c-2eca-4ea1-9747-0d21aeea1708
# Original Author: Liam Monninger
# Contributors: Liam Monninger
# Email: l.mak.monninger@gmail.com
# Organization: Gameday Guru, Inc.
# Date Tagged: 2022-08-11 11:34
# 
# Purpose:
# >
# >
# >
# References:
# -
# -
# -
# 
# License:
# End-User License Agreement (EULA) of Gameday Guru
# This End-User License Agreement ("EULA") is a legal agreement between you and Gameday Guru. Our EULA was created by EULA Template for Gameday Guru.
# 
# This EULA agreement governs your acquisition and use of our Gameday Guru software ("Software") directly from Gameday Guru or indirectly through a Gameday Guru authorized reseller or distributor (a "Reseller").
# 
# Please read this EULA agreement carefully before completing the installation process and using the Gameday Guru software. It provides a license to use the Gameday Guru software and contains warranty information and liability disclaimers.
# 
# If you register for a free trial of the Gameday Guru software, this EULA agreement will also govern that trial. By clicking "accept" or installing and/or using the Gameday Guru software, you are confirming your acceptance of the Software and agreeing to become bound by the terms of this EULA agreement.
# 
# If you are entering into this EULA agreement on behalf of a company or other legal entity, you represent that you have the authority to bind such entity and its affiliates to these terms and conditions. If you do not have such authority or if you do not agree with the terms and conditions of this EULA agreement, do not install or use the Software, and you must not accept this EULA agreement.
# 
# This EULA agreement shall apply only to the Software supplied by Gameday Guru herewith regardless of whether other software is referred to or described herein. The terms also apply to any Gameday Guru updates, supplements, Internet-based services, and support services for the Software, unless other terms accompany those items on delivery. If so, those terms apply.
# 
# License Grant
# Gameday Guru hereby grants you a personal, non-transferable, non-exclusive licence to use the Gameday Guru software on your devices in accordance with the terms of this EULA agreement.
# 
# You are permitted to load the Gameday Guru software (for example a PC, laptop, mobile or tablet) under your control. You are responsible for ensuring your device meets the minimum requirements of the Gameday Guru software.
# 
# You are not permitted to:
# 
# Edit, alter, modify, adapt, translate or otherwise change the whole or any part of the Software nor permit the whole or any part of the Software to be combined with or become incorporated in any other software, nor decompile, disassemble or reverse engineer the Software or attempt to do any such things
# Reproduce, copy, distribute, resell or otherwise use the Software for any commercial purpose
# Allow any third party to use the Software on behalf of or for the benefit of any third party
# Use the Software in any way which breaches any applicable local, national or international law
# use the Software for any purpose that Gameday Guru considers is a breach of this EULA agreement
# Intellectual Property and Ownership
# Gameday Guru shall at all times retain ownership of the Software as originally downloaded by you and all subsequent downloads of the Software by you. The Software (and the copyright, and other intellectual property rights of whatever nature in the Software, including any modifications made thereto) are and shall remain the property of Gameday Guru.
# 
# Gameday Guru reserves the right to grant licences to use the Software to third parties.
# 
# Termination
# This EULA agreement is effective from the date you first use the Software and shall continue until terminated. You may terminate it at any time upon written notice to Gameday Guru.
# 
# It will also terminate immediately if you fail to comply with any term of this EULA agreement. Upon such termination, the licenses granted by this EULA agreement will immediately terminate and you agree to stop all access and use of the Software. The provisions that by their nature continue and survive will survive any termination of this EULA agreement.
# 
# Governing Law
# This EULA agreement, and any dispute arising out of or in connection with this EULA agreement, shall be governed by and construed in accordance with the laws of us.
FROM ubuntu:18.04
COPY . /app
WORKDIR /app

# dependencies
RUN apt update && apt upgrade -y
RUN apt install software-properties-common -y
RUN add-apt-repository ppa:deadsnakes/ppa -y
RUN apt-get install python3.10-full -y
RUN apt install python3.10-venv

# poetry
ENV POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VIRTUALENVS_IN_PROJECT=false \
    POETRY_NO_INTERACTION=1 
ENV PATH="$PATH:$POETRY_HOME/bin"
RUN apt-get update && apt-get install --no-install-recommends -y curl \
    && curl -sSL https://install.python-poetry.org | python3.10 -
# Update poetry to latest version
RUN poetry self update

# venv
ENV VIRTUAL_ENV=/opt/venv
RUN python3.10 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PATH="${PATH}:/root/.local/bin"
RUN ${POETRY_HOME}/bin/poetry install

ENV PYTHONUNBUFFERED=1
ENV PYTHONENCODING="UTF-8"

# entry point
USER 1000
CMD ["python", "-u", "./ncaab_efficiency/model.py"]
