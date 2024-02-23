import config
import logging
import subprocess
from webhooks import send_failed_webhook
import os

env = os.environ.copy()


def train(job):
    command_array = [
        "accelerate", "launch", job['training_script'],
        f"--pretrained_model_name_or_path={job['model_name']}",
        f"--instance_data_dir={config.input_dir}",
        f"--pretrained_vae_model_name_or_path={job['vae_model_name']}",
        f"--output_dir={config.output_dir}",
        f"--instance_prompt=\"{job['prompt']}\"",
        f"--mixed_precision={job['mixed_precision']}",
        f"--resolution={job['resolution']}",
        f"--train_batch_size={job['train_batch_size']}",
        f"--gradient_accumulation_steps={job['gradient_accumulation_steps']}",
        f"--learning_rate={job['learning_rate']}",
        f"--lr_scheduler={job['lr_scheduler']}",
        f"--lr_warmup_steps={job['lr_warmup_steps']}",
        f"--max_train_steps={job['max_training_steps']}",
        f"--checkpointing_steps={job['checkpointing_steps']}",
        "--resume_from_checkpoint=latest",
        "--checkpoints_total_limit=1",
        f"--report_to=wandb",
    ]

    if job["use_8bit_adam"]:
        command_array.append("--use_8bit_adam")

    if job["train_text_encoder"]:
        command_array.append("--train_text_encoder")

    if job["gradient_checkpointing"]:
        command_array.append("--gradient_checkpointing")

    if job["with_prior_preservation"]:
        command_array.append("--with_prior_preservation")
        command_array.append(f"--prior_loss_weight={job['prior_loss_weight']}")

    if job["validation_epochs"] > 0 and job["validation_prompt"] is not None:
        command_array.append(
            f"--validation_prompt=\"{job['validation_prompt']}\"")
        command_array.append(f"--validation_epochs={job['validation_epochs']}")

    logging.info(f"Training command: {' '.join(command_array)}")

    try:
        env["WANDB_NAME"] = job["id"]
        env["WANDB_RUN_ID"] = job["id"]
        subprocess.run(command_array, check=True, env=env)
        logging.info("Training complete.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error: Failed to train model: {e}")
        send_failed_webhook(job["checkpoint_bucket"],
                            job["checkpoint_prefix"], job["id"])
        exit(1)
