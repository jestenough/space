FROM node:24-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    latexmk \
    texlive-xetex \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-lang-cyrillic \
    texlive-fonts-recommended \
    fonts-dejavu \
    fonts-liberation \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

CMD ["make", "build"]
