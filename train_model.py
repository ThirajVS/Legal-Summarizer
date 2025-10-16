import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BartForConditionalGeneration,
    BartTokenizer,
    AdamW,
    get_linear_schedule_with_warmup
)
from rouge_score import rouge_scorer
from tqdm import tqdm
import json
import numpy as np
from typing import List, Dict
import os
import random
from datetime import datetime

class LegalDataset(Dataset):
    def __init__(self, data: List[Dict], tokenizer: BartTokenizer, max_source_length: int = 1024, max_target_length: int = 256):
        self.data = data
        self.tokenizer = tokenizer
        self.max_source_length = max_source_length
        self.max_target_length = max_target_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        source = self.tokenizer(
            item['text'],
            max_length=self.max_source_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        target = self.tokenizer(
            item['summary'],
            max_length=self.max_target_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        return {
            'input_ids': source['input_ids'].squeeze(),
            'attention_mask': source['attention_mask'].squeeze(),
            'labels': target['input_ids'].squeeze()
        }

def load_legal_dataset(data_path: str) -> List[Dict]:
    data = []
    if data_path.endswith('.jsonl'):
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line))
    elif data_path.endswith('.json'):
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    print(f"Loaded {len(data)} training examples")
    return data

def create_synthetic_legal_data(num_samples: int = 100) -> List[Dict]:
    templates = [
        {
            'text': "First Information Report filed on {date} at {location}. Complainant {name} reported theft of mobile phone and wallet. Incident occurred at {time}. Accused is unknown. FIR registered under IPC Section 379.",
            'summary': "Theft case filed under IPC 379. Complainant {name} reported stolen mobile phone and wallet at {location}."
        },
        {
            'text': "Case Number {case_no}. Accused {accused} charged with assault under IPC Section 323. Incident occurred on {date} at {location}. Witness {witness} testified. Medical evidence submitted.",
            'summary': "Assault case under IPC 323. Accused {accused} charged based on witness {witness} testimony and medical evidence."
        },
        {
            'text': "FIR {fir_no} dated {date}. Complainant {complainant} filed complaint against {accused} for fraud under IPC Section 420. Amount involved: Rs. {amount}. Investigation ongoing.",
            'summary': "Fraud case under IPC 420. {complainant} filed complaint against {accused} involving Rs. {amount}."
        }
    ]
    data = []
    for i in range(num_samples):
        template = random.choice(templates)
        names = ['Rajesh Kumar', 'Amit Singh', 'Priya Sharma', 'Vikram Patel']
        locations = ['City Mall', 'Park Street', 'Main Market', 'Railway Station']
        text = template['text'].format(
            date=datetime.now().strftime('%Y-%m-%d'),
            location=random.choice(locations),
            name=random.choice(names),
            accused=random.choice(names),
            witness=random.choice(names),
            complainant=random.choice(names),
            time=f"{random.randint(8,20)}:{random.randint(0,59):02d}",
            case_no=f"CR-{random.randint(100,999)}/2024",
            fir_no=f"FIR-{random.randint(1,1000):04d}",
            amount=f"{random.randint(10,100)},000"
        )
        summary = template['summary'].format(
            name=random.choice(names),
            accused=random.choice(names),
            witness=random.choice(names),
            complainant=random.choice(names),
            location=random.choice(locations),
            amount=f"{random.randint(10,100)},000"
        )
        data.append({'text': text, 'summary': summary})
    return data

def train_legal_bart(train_data: List[Dict], val_data: List[Dict] = None, model_name: str = 'facebook/bart-large-cnn', output_dir: str = 'models/legal_bart', num_epochs: int = 10, batch_size: int = 4, learning_rate: float = 5e-5, warmup_steps: int = 500, save_steps: int = 1000, eval_steps: int = 500):
    print("Starting training...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    tokenizer = BartTokenizer.from_pretrained(model_name)
    model = BartForConditionalGeneration.from_pretrained(model_name)
    model.to(device)
    train_dataset = LegalDataset(train_data, tokenizer)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    if val_data:
        val_dataset = LegalDataset(val_data, tokenizer)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    optimizer = AdamW(model.parameters(), lr=learning_rate)
    total_steps = len(train_loader) * num_epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)
    best_rouge = 0.0
    global_step = 0
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch + 1}/{num_epochs}")
        model.train()
        epoch_loss = 0
        progress_bar = tqdm(train_loader, desc="Training")
        for batch in progress_bar:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            epoch_loss += loss.item()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            global_step += 1
            progress_bar.set_postfix({'loss': loss.item()})
            if val_data and global_step % eval_steps == 0:
                rouge = evaluate_model(model, val_loader, tokenizer, device)
                print(f"\nValidation ROUGE-1: {rouge:.4f}")
                if rouge > best_rouge:
                    best_rouge = rouge
                    save_checkpoint(model, tokenizer, output_dir, global_step)
                    print(f"New best model saved! ROUGE-1: {rouge:.4f}")
                model.train()
            if global_step % save_steps == 0:
                save_checkpoint(model, tokenizer, output_dir, global_step)
        avg_loss = epoch_loss / len(train_loader)
        print(f"Average Loss: {avg_loss:.4f}")
    save_checkpoint(model, tokenizer, output_dir, 'final')
    print(f"Training complete! Model saved to {output_dir}")

def evaluate_model(model, val_loader, tokenizer, device) -> float:
    model.eval()
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    all_rouge1 = []
    with torch.no_grad():
        for batch in tqdm(val_loader, desc="Evaluating"):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            generated = model.generate(input_ids=input_ids, attention_mask=attention_mask, max_length=256, num_beams=4, early_stopping=True)
            generated_texts = tokenizer.batch_decode(generated, skip_special_tokens=True)
            reference_texts = tokenizer.batch_decode(batch['labels'], skip_special_tokens=True)
            for gen, ref in zip(generated_texts, reference_texts):
                scores = scorer.score(ref, gen)
                all_rouge1.append(scores['rouge1'].fmeasure)
    return np.mean(all_rouge1)

def save_checkpoint(model, tokenizer, output_dir, step):
    checkpoint_dir = os.path.join(output_dir, f'checkpoint-{step}')
    os.makedirs(checkpoint_dir, exist_ok=True)
    model.save_pretrained(checkpoint_dir)
    tokenizer.save_pretrained(checkpoint_dir)
    print(f"Checkpoint saved to {checkpoint_dir}")

def main():
    print("Generating synthetic training data...")
    all_data = create_synthetic_legal_data(num_samples=500)
    split_idx = int(0.8 * len(all_data))
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]
    print(f"Train: {len(train_data)}, Val: {len(val_data)}")
    train_legal_bart(train_data=train_data, val_data=val_data, model_name='facebook/bart-base', output_dir='models/legal_bart', num_epochs=3, batch_size=8, learning_rate=3e-5)

if __name__ == '__main__':
    main()
