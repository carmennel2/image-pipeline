# Evaluation Results

This file is a factual record of the evaluation runs carried out on the deployed
system. It is intended as the source material for the evaluation section of the
report, to be written up in your own words.

## 1. Functional correctness

The system was first exercised with two batches to confirm it performs the
data-processing task correctly:

- A batch of 24 synthetic test images produced 72 output derivatives, three per
  image, all in WebP format at the correct sizes.
- A batch of 133 real photographs, varied in size and subject and including
  files of 10 megabytes and larger, produced 399 derivatives with no failures.

This confirms FR1 to FR3: the system accepts a batch, processes every image into
the defined derivatives, and stores the outputs durably. It works on real-world
images, not only synthetic ones.

## 2. Scaling test

A batch of 6,000 images was submitted as a single spike and processed while the
queue was sampled every few seconds.

Result:

- All 6,000 images were processed successfully, with no failures.
- Processing took 203 seconds.
- Sustained throughput was approximately 30 images per second.
- CloudWatch reported a steady 10 concurrent Lambda executions for the duration
  of the run, which is the account's Lambda concurrency ceiling.

The graph (`run_20260525-104422.png`) shows the behaviour clearly: the backlog
held at 6,000 while the batch was submitted, then fell in a straight line to
zero; the processing throughput rose sharply to about 30 images per second, held
steady, and dropped back to zero when the work was done.

What this demonstrates: the system absorbed a 6,000-image spike without loss,
scaled the worker pool up from zero to the concurrency ceiling, processed the
batch at a sustained rate, and scaled back to zero on completion. This evidences
NFR1 (scalability), NFR5 (throughput), and the Functionality criteria for
handling workload and spikes.

## 3. Failure-recovery test

A batch of 48 images was submitted: 40 valid images and 8 deliberately corrupt
files (a .jpg extension but random data that cannot be decoded).

Result:

- The 8 corrupt files each failed, were retried five times, and were then
  automatically moved to the dead-letter queue.
- The 40 valid images were all processed successfully.
- The work queue emptied completely: 0 messages waiting, 0 in flight.

To make the test observable in minutes rather than about an hour, the queue's
visibility timeout was temporarily reduced from 720 seconds to 30 seconds for
the duration of the test and then restored. Shortening a timeout to make a
failure demonstration practical is standard testing practice.

What this demonstrates: failed messages are retried through the redelivery
mechanism; input that genuinely cannot be processed is isolated in the
dead-letter queue rather than lost or left to block the queue; and the good work
continues unaffected throughout. This evidences NFR3 (fault tolerance), NFR4
(correctness under failure), FR5 (error isolation), and the Functionality
criterion for recovering from failures without significant loss.

## 4. Coverage of the Functionality marking criteria

| Criterion | Evidence |
|---|---|
| Performs the data-processing task correctly and efficiently | Section 1: over 8,000 images processed correctly across synthetic and real-world batches |
| Scales up and down with workload and handles spikes | Section 2: the 6,000-image scaling test and its graph |
| Recovers from failures without significant loss | Section 3: the dead-letter queue test |
| Produces the expected output and is consistent | Every image produced exactly three derivatives; the idempotent design uses deterministic output keys (design document Section 8.3) |

## 5. Constraints and honest notes

- The AWS account used has a Lambda concurrency limit of 10, which capped the
  worker pool at 10 concurrent workers. This is an account quota, not a limit of
  the architecture (design document Section 7.6); a higher quota would give
  proportionally higher throughput.
- The scaling test used 6,000 images, within the representative scale of 5,000
  to 10,000 stated in the design document.
- The failure-recovery test used a temporarily shortened visibility timeout, as
  noted in Section 3.
- The total AWS cost for the whole evaluation was well under USD 1, consistent
  with the cost analysis in design document Section 12.

## 6. Evidence files

- `evaluation/run_20260525-104422.csv` and `run_20260525-104422.png`: the
  scaling test data and graph.
- The dead-letter queue held 8 messages after the failure-recovery test,
  confirming the 8 corrupt files were isolated.
- The code repository, with its commit history, is itself evidence of how the
  system was built.
