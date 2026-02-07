from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
import logging

# Import models
from .models import Course, Enrollment, Question, Choice, Submission

logger = logging.getLogger(__name__)

# ===========================
# AUTH VIEWS
# ===========================

def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        try:
            User.objects.get(username=username)
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
        except:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            login(request, user)
            return redirect("onlinecourse:index")


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


# ===========================
# HELPER FUNCTION
# ===========================

def check_if_enrolled(user, course):
    if user.is_authenticated:
        return Enrollment.objects.filter(user=user, course=course).exists()
    return False


# ===========================
# COURSE LIST & DETAIL
# ===========================

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

    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(
        reverse(viewname='onlinecourse:course_detail', args=(course.id,))
    )


# ===========================
# TASK 5 — EXAM LOGIC (FIXED)
# ===========================

def extract_answers(request):
    """
    Collect selected choice IDs from POST data
    """
    selected_ids = []
    for key, value in request.POST.items():
        if key.startswith("choice_"):
            selected_ids.append(int(value))
    return Choice.objects.filter(id__in=selected_ids)


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    enrollment = Enrollment.objects.get(user=user, course=course)

    submission = Submission.objects.create(enrollment=enrollment)
    choices = extract_answers(request)
    submission.choices.set(choices)

    submission_id = submission.id

    return HttpResponseRedirect(
        reverse('onlinecourse:exam_result', args=(course_id, submission_id))
    )


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, id=submission_id)

    choices = submission.choices.all()

    total_questions = course.question_set.count()
    correct_answers = 0

    for choice in choices:
        if choice.is_correct:
            correct_answers += 1

    score = correct_answers
    total = total_questions

    context = {
        "course": course,
        "submission": submission,
        "choices": choices,
        "score": score,
        "total": total,
    }

    return render(request, "onlinecourse/exam_result_bootstrap.html", context)
