
import os
import pytest
from pycondor import Job, Dagman
from pycondor.utils import clear_pycondor_environment_variables

clear_pycondor_environment_variables()

example_script = os.path.join('examples', 'savelist.py')


@pytest.fixture()
def job(tmpdir_factory):
    submit_dir = str(tmpdir_factory.mktemp('submit'))
    job = Job('jobname', example_script, submit=submit_dir)
    return job


def test_add_arg_type_fail(job):
    with pytest.raises(TypeError) as excinfo:
        job.add_arg(50)
    error = 'arg must be a string'
    assert error == str(excinfo.value)


def test_add_arg_name_type_fail(job):
    with pytest.raises(TypeError) as excinfo:
        job.add_arg('arg', name=23.12)
    error = 'name must be a string'
    assert error == str(excinfo.value)


def test_add_arg_retry_type_fail(job):
    with pytest.raises(TypeError) as excinfo:
        job.add_arg('arg', retry='10')
    error = 'retry must be an int'
    assert error == str(excinfo.value)


def test_add_child_type_fail(job):
    with pytest.raises(TypeError) as excinfo:
        job.add_child('childjob')
    error = 'add_child() is expecting a Job or Dagman instance. ' + \
            'Got an object of type {}'.format(type('childjob'))
    assert error == str(excinfo.value)


def test_add_children_type_fail(job):
    with pytest.raises(TypeError):
        job.add_children([1, 2, 3, 4])


def test_add_parent_type_fail(job):
    with pytest.raises(TypeError) as excinfo:
        job.add_parent('parentjob')
    error = 'add_parent() is expecting a Job or Dagman instance. ' + \
            'Got an object of type {}'.format(type('parentjob'))
    assert error == str(excinfo.value)


def test_add_parents_type_fail(job):
    with pytest.raises(TypeError):
        job.add_parents([1, 2, 3, 4])


def test_build_executeable_not_found_fail(tmpdir):
    submit_dir = str(tmpdir.join('submit'))
    with pytest.raises(IOError) as excinfo:
        ex = '/path/to/executable'
        job = Job('jobname', ex, submit=submit_dir)
        job.build(makedirs=False)
    error = 'The executable {} does not exist'.format(ex)
    assert error == str(excinfo.value)


def test_queue_written_to_submit_file(tmpdir):
    # Test to check that the queue parameter is properly written
    # to submit file when Job is created. See issue #38.

    submit_dir = str(tmpdir.mkdir('submit'))

    # Build Job object with queue=5
    job = Job('jobname', example_script, submit=submit_dir, queue=5)
    job.build(fancyname=False)

    # Read the built submit file and check that the 'queue 5' is
    # contained in the file.
    with open(job.submit_file, 'r') as f:
        lines = f.readlines()
    assert 'queue 5' in lines


@pytest.mark.parametrize('env_var', ['output', 'error', 'log'])
def test_job_env_variable_dir(tmpdir, monkeypatch, env_var):
    # Use monkeypatch fixture to set pycondor environment variable
    dir_path = str(tmpdir.mkdir(env_var))
    monkeypatch.setenv('PYCONDOR_{}_DIR'.format(env_var.upper()), dir_path)

    submit_dir = str(tmpdir.join('submit'))

    job = Job('jobname', example_script, submit=submit_dir)
    job.build()
    tmpdir_path = os.path.join(str(tmpdir), env_var)
    job_path = os.path.dirname(getattr(job, '{}_file'.format(env_var)))
    assert tmpdir_path == job_path


def test_job_submit_env_variable(tmpdir, monkeypatch):
    # Use monkeypatch fixture to set pycondor environment variable
    dir_path = str(tmpdir.mkdir('submit'))
    monkeypatch.setenv('PYCONDOR_SUBMIT_DIR', dir_path)

    job = Job('jobname', example_script)
    job.build()
    tmpdir_path = os.path.join(str(tmpdir), 'submit')
    job_path = os.path.dirname(getattr(job, 'submit_file'))
    assert tmpdir_path == job_path


def test_repr():
    default_job = Job('jobname', example_script)
    job_repr = repr(default_job)
    expected_repr = ('Job(name=jobname, executable=savelist.py, '
                     'getenv=True, notification=never, submit={}, '
                     'universe=vanilla)'.format(os.getcwd()))
    assert job_repr == expected_repr

    job_non_default = Job('jobname', example_script, queue=2)
    job_repr = repr(job_non_default)
    expected_repr = ('Job(name=jobname, executable=savelist.py, getenv=True, '
                     'notification=never, queue=2, submit={}, '
                     'universe=vanilla)'.format(os.getcwd()))
    assert job_repr == expected_repr


def test_submit_job_not_built_raises(job):
    with pytest.raises(ValueError) as excinfo:
        job.submit_job()
    error = 'build() must be called before submit()'
    assert error == str(excinfo.value)


def test_submit_job_parents_raises(tmpdir):
    # Test submitting a Job with parents (not in a Dagman) raises an error
    submit = str(tmpdir)
    job = Job('jobname', example_script, submit=submit)
    parent_job = Job('parent_jobname', example_script, submit=submit)
    job.add_parent(parent_job)
    job.build()
    with pytest.raises(ValueError) as excinfo:
        job.submit_job()
    error = ('Attempting to submit a Job with parents. '
             'Interjob relationships requires Dagman.')
    assert error == str(excinfo.value)


def test_submit_job_children_raises(tmpdir, job):
    # Test submitting a Job with children (not in a Dagman) raises an error
    submit = str(tmpdir)
    child_job = Job('child_jobname', example_script, submit=submit)
    job.add_child(child_job)
    job.build()
    with pytest.raises(ValueError) as excinfo:
        job.submit_job()
    error = ('Attempting to submit a Job with children. '
             'Interjob relationships requires Dagman.')
    assert error == str(excinfo.value)


def test_submit_job_kwargs_deprecation_message(tmpdir, job):
    job.build()
    with pytest.deprecated_call():
        kwargs = {'-maxjobs': 1000}
        job.submit_job(**kwargs)


def test_add_args_raises(job):
    # Test that add_args won't accept non-iterable argument inputs
    args = 10
    with pytest.raises(TypeError):
        job.add_args(args)


def test_add_args():
    # Test that add_args is equivalent to multiple add_arg
    job_1 = Job('job1', example_script)
    for i in range(10):
        job_1.add_arg('file_{}.hdf'.format(i))

    job_2 = Job('job2', example_script)
    job_2.add_args(['file_{}.hdf'.format(i) for i in range(10)])

    assert job_1.args == job_2.args


def test_retry_job_raises(job):
    # Test that building a Job (not in a Dagman) with a retry raises an error
    job.add_arg('argument', retry=2)
    with pytest.raises(NotImplementedError) as excinfo:
        job.build()
    error = ('Retrying failed Jobs is only available when submitting '
             'from a Dagman.')
    assert error == str(excinfo.value)


def test_job_dag_parameter():
    dag = Dagman('dagman')
    job = Job('job', example_script, dag=dag)

    assert job in dag


def test_add_job_dag_parameter_equality(tmpdir):
    submit_dir = str(tmpdir.join('submit'))
    dag = Dagman('dagman', submit=submit_dir)
    job_1 = Job('job_1', example_script, dag=dag)
    job_2 = Job('job_2', example_script)
    dag.add_job(job_2)

    assert dag.nodes == [job_1, job_2]


def test_job_len_initial(job):
    assert len(job) == 0


def test_dagman_len_initial(job):
    job.add_args(str(i) for i in range(10))
    assert len(job) == 10


def test_job_subdag_build(tmpdir):
    submit_dir = str(tmpdir.join('submit'))

    extra_lines = ['first extra line', 'second extra line']
    job = Job('job', example_script,
              submit=submit_dir,
              extra_lines=extra_lines)
    job.build()

    with open(job.submit_file, 'r') as f:
        assert set(extra_lines) <= set(line.rstrip('\n') for line in f)


def test_job_args_and_queue_raises(tmpdir):
    submit_dir = str(tmpdir.join('submit'))

    with pytest.raises(NotImplementedError) as excinfo:
        job = Job('job', example_script,
                  submit=submit_dir,
                  queue=2)
        job.add_args(str(i) for i in range(10))
        job.build()
    error = ('At this time multiple arguments and queue values '
             'are only supported through Dagman')
    assert error == str(excinfo.value)


def test_job_args_warning(caplog, job):
    job.add_args(str(i) for i in range(20))
    job.build()
    log_message = 'Consider using a Dagman in the future to help monitor jobs'
    assert log_message in caplog.text


def test_job_context_manager_enter(job):
    assert job.__enter__() is job
