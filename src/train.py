import config
import logging
import subprocess
from webhooks import send_failed_webhook
import os
import time

env = os.environ.copy()


def job_to_command_array(job):
    command_array = [
        "accelerate", "launch", job['training_script'],
        f"--pretrained_model_name_or_path={job['pretrained_model_name_or_path']}",
        f"--instance_data_dir={config.instance_dir}",
        f"--pretrained_vae_model_name_or_path={job['pretrained_vae_model_name_or_path']}",
        f"--output_dir={config.output_dir}",
        f"--instance_prompt=\"{job['instance_prompt']}\"",
        f"--mixed_precision={job['mixed_precision']}",
        f"--resolution={job['resolution']}",
        f"--train_batch_size={job['train_batch_size']}",
        f"--gradient_accumulation_steps={job['gradient_accumulation_steps']}",
        f"--learning_rate={job['learning_rate']}",
        f"--lr_scheduler={job['lr_scheduler']}",
        f"--lr_warmup_steps={job['lr_warmup_steps']}",
        f"--checkpointing_steps={job['checkpointing_steps']}",
        '--seed=0',
        "--resume_from_checkpoint=latest",
        "--checkpoints_total_limit=1",
    ]

    if job["num_train_epochs"] > 1:
        command_array.append(f"--num_train_epochs={job['num_train_epochs']}")
    else:
        command_array.append(f"--max_train_steps={job['max_train_steps']}")

    if job["center_crop"]:
        command_array.append("--center_crop")

    if job["random_flip"]:
        command_array.append("--random_flip")

    if job["use_8bit_adam"]:
        command_array.append("--use_8bit_adam")

    if job["train_text_encoder"]:
        command_array.append("--train_text_encoder")
        command_array.append(
            f"--text_encoder_lr={job['text_encoder_lr']}")

    if job["gradient_checkpointing"]:
        command_array.append("--gradient_checkpointing")

    if job["with_prior_preservation"]:
        command_array.append("--with_prior_preservation")
        command_array.append(f"--class_data_dir={config.class_dir}")

        if 'prior_loss_weight' in job:
            command_array.append(
                f"--prior_loss_weight={job['prior_loss_weight']}")

        if "class_prompt" in job:
            command_array.append(f"--class_prompt=\"{job['class_prompt']}\"")

        if "num_class_images" in job:
            command_array.append(
                f"--num_class_images={job['num_class_images']}")

    if job["validation_epochs"] > 0 and job["validation_prompt"] is not None:
        command_array.append(
            f"--validation_prompt=\"{job['validation_prompt']}\"")
        command_array.append(f"--validation_epochs={job['validation_epochs']}")
        command_array.append(f"--sample_batch_size={job['sample_batch_size']}")

    if config.wandb_api_key is not None:
        command_array.append(f"--report_to=wandb")

    return command_array


def train(job, stop_signal):
    command_array = job_to_command_array(job)

    logging.info(f"Training command: {' '.join(command_array)}")

    try:
        env["WANDB_NAME"] = job["id"]
        env["WANDB_RUN_ID"] = job["id"]
        process = subprocess.Popen(command_array, env=env)

        while process.poll() is None:
            if stop_signal.is_set():
                logging.info(
                    "Received stop signal. Terminating training process.")
                process.terminate()
                process.wait()
                return
            time.sleep(1)
        stop_signal.set()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode, command_array)
        logging.info("Training complete.")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error: Failed to train model: {e}")
        send_failed_webhook(job["checkpoint_bucket"],
                            job["checkpoint_prefix"], job["id"])
        stop_signal.set()
        exit(1)
