Khorovod
=======

Horovod is a distributed deep learning training framework for TensorFlow, Keras, PyTorch, and Apache MXNet.
The goal of Horovod is to make distributed deep learning fast and easy to use.


The primary motivation for this project is to make it easy to take a single-GPU training script and successfully scale
it to train across many GPUs in parallel. This has two aspects:

1. How much modification does one have to make to a program to make it distributed, and how easy is it to run it?
2. How much faster would it run in distributed mode?

Internally at Uber we found the MPI model to be much more straightforward and require far less code changes than previous
solutions such as Distributed TensorFlow with parameter servers. Once a training script has been written for scale with
Horovod, it can run on a single-GPU, multiple-GPUs, or even multiple hosts without any further code changes.
See the `Usage <#usage>`__ section for more details.

In addition to being easy to use, Horovod is fast. Below is a chart representing the benchmark that was done on 128
servers with 4 Pascal GPUs each connected by RoCE-capable 25 Gbit/s network:

.. image:: https://user-images.githubusercontent.com/16640218/38965607-bf5c46ca-4332-11e8-895a-b9c137e86013.png
   :alt: 512-GPU Benchmark

Horovod achieves 90% scaling efficiency for both Inception V3 and ResNet-101, and 68% scaling efficiency for VGG-16.
See `Benchmarks <docs/benchmarks.rst>`_ to find out how to reproduce these numbers.

While installing MPI and NCCL itself may seem like an extra hassle, it only needs to be done once by the team dealing
with infrastructure, while everyone else in the company who builds the models can enjoy the simplicity of training them at
scale.


Install
-------
To install Horovod on Linux or macOS:

1. Install `CMake <https://cmake.org/install/>`__

.. raw:: html

    <p/>

2. If you've installed TensorFlow from `PyPI <https://pypi.org/project/tensorflow>`__, make sure that ``g++-5`` or above is installed.
   Starting with TensorFlow 2.10 a C++17-compliant compiler like ``g++8`` or above will be required.

   If you've installed PyTorch from `PyPI <https://pypi.org/project/torch>`__, make sure that ``g++-5`` or above is installed.

   If you've installed either package from `Conda <https://conda.io>`_, make sure that the ``gxx_linux-64`` Conda package is installed.

.. raw:: html

    <p/>

3. Install the ``horovod`` pip package.

   To run on CPUs:

   .. code-block:: bash

      $ pip install horovod

   To run on GPUs with NCCL:

   .. code-block:: bash

      $ HOROVOD_GPU_OPERATIONS=NCCL pip install horovod

For more details on installing Horovod with GPU support, read `Horovod on GPU <docs/gpus.rst>`_.

For the full list of Horovod installation options, read the `Installation Guide <docs/install.rst>`_.

If you want to use MPI, read `Horovod with MPI <docs/mpi.rst>`_.

If you want to use Conda, read `Building a Conda environment with GPU support for Horovod <docs/conda.rst>`_.

If you want to use Docker, read `Horovod in Docker <docs/docker.rst>`_.

To compile Horovod from source, follow the instructions in the `Contributor Guide <docs/contributors.rst>`_.


Concepts
--------
Horovod core principles are based on `MPI <http://mpi-forum.org/>`_ concepts such as *size*, *rank*,
*local rank*, **allreduce**, **allgather**, **broadcast**, and **alltoall**. See `this page <docs/concepts.rst>`_
for more details.

Supported frameworks
--------------------
See these pages for Horovod examples and best practices:

- `Horovod with TensorFlow <docs/tensorflow.rst>`_
- `Horovod with XLA in Tensorflow <xla.rst>`_
- `Horovod with Keras <docs/keras.rst>`_
- `Horovod with PyTorch <docs/pytorch.rst>`_
- `Horovod with MXNet <docs/mxnet.rst>`_

Usage
-----

To use Horovod, make the following additions to your program:

1. Run ``hvd.init()`` to initialize Horovod.

.. raw:: html

    <p/>

2. Pin each GPU to a single process to avoid resource contention.

   With the typical setup of one GPU per process, set this to *local rank*. The first process on
   the server will be allocated the first GPU, the second process will be allocated the second GPU, and so forth.

.. raw:: html

    <p/>


3. Scale the learning rate by the number of workers.

   Effective batch size in synchronous distributed training is scaled by the number of workers.
   An increase in learning rate compensates for the increased batch size.

.. raw:: html

    <p/>


4. Wrap the optimizer in ``hvd.DistributedOptimizer``.

   The distributed optimizer delegates gradient computation to the original optimizer, averages gradients using **allreduce** or **allgather**, and then applies those averaged gradients.

.. raw:: html

    <p/>


5. Broadcast the initial variable states from rank 0 to all other processes.

   This is necessary to ensure consistent initialization of all workers when training is started with random weights or restored from a checkpoint.

.. raw:: html

    <p/>


6. Modify your code to save checkpoints only on worker 0 to prevent other workers from corrupting them.

.. raw:: html

    <p/>


Example using TensorFlow v1 (see the `examples <https://github.com/horovod/horovod/blob/master/examples/>`_ directory for full training examples):

.. code-block:: python

    import tensorflow as tf
    import horovod.tensorflow as hvd


    # Initialize Horovod
    hvd.init()

    # Pin GPU to be used to process local rank (one GPU per process)
    config = tf.ConfigProto()
    config.gpu_options.visible_device_list = str(hvd.local_rank())

    # Build model...
    loss = ...
    opt = tf.train.AdagradOptimizer(0.01 * hvd.size())

    # Add Horovod Distributed Optimizer
    opt = hvd.DistributedOptimizer(opt)

    # Add hook to broadcast variables from rank 0 to all other processes during
    # initialization.
    hooks = [hvd.BroadcastGlobalVariablesHook(0)]

    # Make training operation
    train_op = opt.minimize(loss)

    # Save checkpoints only on worker 0 to prevent other workers from corrupting them.
    checkpoint_dir = '/tmp/train_logs' if hvd.rank() == 0 else None

    # The MonitoredTrainingSession takes care of session initialization,
    # restoring from a checkpoint, saving to a checkpoint, and closing when done
    # or an error occurs.
    with tf.train.MonitoredTrainingSession(checkpoint_dir=checkpoint_dir,
                                           config=config,
                                           hooks=hooks) as mon_sess:
      while not mon_sess.should_stop():
        # Perform synchronous training.
        mon_sess.run(train_op)


Running Horovod
---------------
The example commands below show how to run distributed training.
See `Run Horovod <docs/running.rst>`_ for more details, including RoCE/InfiniBand tweaks and tips for dealing with hangs.

1. To run on a machine with 4 GPUs:

   .. code-block:: bash

        $ horovodrun -np 4 -H localhost:4 python train.py

2. To run on 4 machines with 4 GPUs each:

   .. code-block:: bash

       $ horovodrun -np 16 -H server1:4,server2:4,server3:4,server4:4 python train.py

3. To run using Open MPI without the ``horovodrun`` wrapper, see `Running Horovod with Open MPI <docs/mpi.rst>`_.

4. To run in Docker, see `Horovod in Docker <docs/docker.rst>`_.

5. To run on Kubernetes, see `Helm Chart <https://github.com/horovod/horovod/tree/master/docker/helm/>`_, `Kubeflow MPI Operator <https://github.com/kubeflow/mpi-operator/>`_, `FfDL <https://github.com/IBM/FfDL/tree/master/etc/examples/horovod/>`_, and `Polyaxon <https://docs.polyaxon.com/integrations/horovod/>`_.

6. To run on Spark, see `Horovod on Spark <docs/spark.rst>`_.

7. To run on Ray, see `Horovod on Ray <docs/ray.rst>`_.

8. To run in Singularity, see `Singularity <https://github.com/sylabs/examples/tree/master/machinelearning/horovod>`_.

9. To run in a LSF HPC cluster (e.g. Summit), see `LSF <docs/lsf.rst>`_.

10. To run on Hadoop Yarn, see `TonY <https://github.com/linkedin/TonY/>`_.

Gloo
----
`Gloo <https://github.com/facebookincubator/gloo>`_ is an open source collective communications library developed by Facebook.

Gloo comes included with Horovod, and allows users to run Horovod without requiring MPI to be installed.

For environments that have support both MPI and Gloo, you can choose to use Gloo at runtime by passing the ``--gloo`` argument to ``horovodrun``:

.. code-block:: bash

     $ horovodrun --gloo -np 2 python train.py

mpi4py
------
Horovod supports mixing and matching Horovod collectives with other MPI libraries, such as `mpi4py <https://mpi4py.scipy.org>`_,
provided that the MPI was built with multi-threading support.

You can check for MPI multi-threading support by querying the ``hvd.mpi_threads_supported()`` function.

.. code-block:: python

    import horovod.tensorflow as hvd

    # Initialize Horovod
    hvd.init()

    # Verify that MPI multi-threading is supported.
    assert hvd.mpi_threads_supported()

    from mpi4py import MPI
    assert hvd.size() == MPI.COMM_WORLD.Get_size()

You can also initialize Horovod with an `mpi4py` sub-communicator, in which case each sub-communicator
will run an independent Horovod training.

.. code-block:: python

    from mpi4py import MPI
    import horovod.tensorflow as hvd

    # Split COMM_WORLD into subcommunicators
    subcomm = MPI.COMM_WORLD.Split(color=MPI.COMM_WORLD.rank % 2,
                                   key=MPI.COMM_WORLD.rank)

    # Initialize Horovod
    hvd.init(comm=subcomm)

    print('COMM_WORLD rank: %d, Horovod rank: %d' % (MPI.COMM_WORLD.rank, hvd.rank()))


Inference
---------
Learn how to optimize your model for inference and remove Horovod operations from the graph `here <docs/inference.rst>`_.


Tensor Fusion
-------------
One of the unique things about Horovod is its ability to interleave communication and computation coupled with the ability
to batch small **allreduce** operations, which results in improved performance. We call this batching feature Tensor Fusion.

See `here <docs/tensor-fusion.rst>`__ for full details and tweaking instructions.


Horovod Timeline
----------------
Horovod has the ability to record the timeline of its activity, called Horovod Timeline.

.. image:: https://user-images.githubusercontent.com/16640218/29735271-9e148da0-89ac-11e7-9ae0-11d7a099ac89.png
   :alt: Horovod Timeline

Use Horovod timeline to analyze Horovod performance.
See `here <docs/timeline.rst>`__ for full details and usage instructions.


Automated Performance Tuning
----------------------------
Selecting the right values to efficiently make use of Tensor Fusion and other advanced Horovod features can involve
a good amount of trial and error. We provide a system to automate this performance optimization process called
**autotuning**, which you can enable with a single command line argument to ``horovodrun``.

See `here <docs/autotune.rst>`__ for full details and usage instructions.


Horovod Process Sets
--------------------
Horovod allows you to concurrently run distinct collective operations in different groups of processes taking part in
one distributed training. Set up ``hvd.process_set`` objects to make use of this capability.

See `Process Sets <docs/process_set.rst>`__ for detailed instructions.


Troubleshooting
---------------
See `Troubleshooting <docs/troubleshooting.rst>`_ and submit a `ticket <https://github.com/horovod/horovod/issues/new>`_
if you can't find an answer.


Citation
--------
Please cite Horovod in your publications if it helps your research:

::

    @article{sergeev2018horovod,
      Author = {Alexander Sergeev and Mike Del Balso},
      Journal = {arXiv preprint arXiv:1802.05799},
      Title = {Horovod: fast and easy distributed deep learning in {TensorFlow}},
      Year = {2018}
    }


Publications
------------
1. Sergeev, A., Del Balso, M. (2017) *Meet Horovod: Uber’s Open Source Distributed Deep Learning Framework for TensorFlow*.
Retrieved from `https://eng.uber.com/horovod/ <https://eng.uber.com/horovod/>`_

2. Sergeev, A. (2017) *Horovod - Distributed TensorFlow Made Easy*. Retrieved from
`https://www.slideshare.net/AlexanderSergeev4/horovod-distributed-tensorflow-made-easy <https://www.slideshare.net/AlexanderSergeev4/horovod-distributed-tensorflow-made-easy>`_

3. Sergeev, A., Del Balso, M. (2018) *Horovod: fast and easy distributed deep learning in TensorFlow*. Retrieved from
`arXiv:1802.05799 <https://arxiv.org/abs/1802.05799>`_


References
----------
The Horovod source code was based off the Baidu `tensorflow-allreduce <https://github.com/baidu-research/tensorflow-allreduce>`_
repository written by Andrew Gibiansky and Joel Hestness. Their original work is described in the article
`Bringing HPC Techniques to Deep Learning <http://andrew.gibiansky.com/blog/machine-learning/baidu-allreduce/>`_.
