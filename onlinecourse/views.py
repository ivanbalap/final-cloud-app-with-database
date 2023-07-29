from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment
from .models import Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment=Enrollment.objects.get(user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    for choice_id in extract_answers(request):
        submission.choices.add(Choice.objects.get(id=choice_id))
    submission.save()
    return show_exam_result(request,course_id, submission.id)


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    context=dict()
    course = get_object_or_404(Course, pk=course_id)
    submission = Submission.objects.get(id=submission_id)
    selected_ids=set()
    question_ids=set()
    total_correct_choice=0
    course_total_correct_choice=0
    grade=0
    course_total_grade=0

    context['questions_answered'] =dict()
    for choice in submission.choices.all():
        selected_ids.add(choice.id)
        question_ids.add(choice.question.id)
        if not ( choice.question.id in context['questions_answered'] ):
            context['questions_answered'][choice.question.id]=set()
        context['questions_answered'][choice.question.id].add(choice.id)
        if choice.choice_is_correct:
            total_correct_choice+=1

    # for lesson in submission.enrollment.course.lesson_set.all():
    #     for question in lesson.question_set.all():
    #         for choice in question.choice_set.all():
    #             if choice.choice_is_correct:
    #                 course_total_correct_choice+=1
    
    context['questions'] =dict()
    for question_id in question_ids:
        # context['questions'].add(question_id)
        context['questions'][question_id] = [set(choice['id'] for choice in Question.objects.get(id=question_id).choice_set.all().filter(choice_is_correct=True).values('id')),Question.objects.get(id=question_id).question_grade]
    
    # grade=round(total_correct_choice/course_total_correct_choice*100,2)
    
    grade=0
    for question_id in context['questions'].keys():
        if context['questions'][question_id][0] == context['questions_answered'][question_id]:
            grade+=context['questions'][question_id][1]
        course_total_grade+=context['questions'][question_id][1]
    
    context['course']=course
    context['selected_ids']=selected_ids
    context['grade']=round(grade/course_total_grade*100,2)
    context['grade_str']=str(int(grade)) + ' / ' + str(int(course_total_grade))
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
