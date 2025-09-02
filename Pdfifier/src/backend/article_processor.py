"""
ArticleProcessor: Main class for processing articles from CSV links and generating PDFs.
- Reads CSV file of article links
- Extracts text and images from each link
- Generates PDF for each article
- Tracks processed links to avoid duplicates
- Exception handling and logging
"""
import os
import csv
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
from dotenv import load_dotenv

class ArticleProcessor:
    def __init__(self, csv_path, output_dir, processed_links_path):
        """
        Initialize processor with paths and load processed links.
        """
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.processed_links_path = processed_links_path
        self.processed_links = self._load_processed_links()
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def _load_processed_links(self):
        """
        Load processed links from file to avoid reprocessing.
        """
        if not os.path.exists(self.processed_links_path):
            return set()
        with open(self.processed_links_path, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())

    def _save_processed_link(self, link):
        """
        Save a processed link to the tracking file.
        """
        with open(self.processed_links_path, 'a', encoding='utf-8') as f:
            f.write(link + '\n')
        self.processed_links.add(link)

    def process_articles(self):
        """
        Main method to process articles from CSV and generate PDFs.
        """
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    for link in row:
                        link = link.strip()
                        if not link or link in self.processed_links:
                            continue  # Skip empty or already processed
                        try:
                            print(f"Processing: {link}")
                            article = Article(link)
                            article.fetch_content()
                            pdf_path = os.path.join(self.output_dir, f"{article.safe_title()}.pdf")
                            article.to_pdf(pdf_path)
                            self._save_processed_link(link)
                        except Exception as e:
                            print(f"Error processing {link}: {e}")
        except Exception as e:
            print(f"Failed to process articles: {e}")

class Article:
    def __init__(self, url):
        """
        Initialize with article URL.
        """
        self.url = url
        self.title = None
        self.text = None
        self.images = []

    def fetch_content(self):
        """
        Fetch and parse article content (text and images).
        """
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            self.title = soup.title.string if soup.title else 'untitled'
            self.text = self._extract_text(soup)
            self.images = self._extract_images(soup)
        except Exception as e:
            raise Exception(f"Failed to fetch content from {self.url}: {e}")

    def _extract_text(self, soup):
        """
        Extract main text from the article.
        """
        paragraphs = soup.find_all('p')
        return '\n'.join(p.get_text() for p in paragraphs)

    def _extract_images(self, soup):
        """
        Extract image URLs from the article.
        """
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and src.startswith('http'):
                images.append(src)
        return images

    def safe_title(self):
        """
        Generate a safe filename from the article title.
        """
        return ''.join(c if c.isalnum() else '_' for c in (self.title or 'untitled'))

    def to_pdf(self, pdf_path):
        """
        Generate a PDF from the article's text and images.
        """
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            pdf.cell(0, 10, self.title, ln=True)
            pdf.set_font('Arial', '', 12)
            pdf.multi_cell(0, 10, self.text)
            for img_url in self.images:
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    img_path = pdf_path + '_img.jpg'
                    with open(img_path, 'wb') as img_file:
                        img_file.write(img_data)
                    pdf.image(img_path, w=100)
                    os.remove(img_path)
                except Exception as e:
                    print(f"Failed to add image {img_url}: {e}")
            pdf.output(pdf_path)
        except Exception as e:
            raise Exception(f"Failed to generate PDF for {self.url}: {e}")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env/.env'))
    csv_path = os.path.join(os.path.dirname(__file__), '../data/articles.csv')
    output_dir = os.getenv('PDF_OUTPUT_DIR', os.path.join(os.path.dirname(__file__), '../data/output_pdfs'))
    processed_links_path = os.path.join(os.path.dirname(__file__), '../data/processed_links.txt')
    processor = ArticleProcessor(csv_path, output_dir, processed_links_path)
    processor.process_articles()
