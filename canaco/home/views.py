from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
import os
from .import urls
from .models import Archivo, Categoria, Comentario, GaleriaPublicacion, Perfil, Publicacion
from django.core.files.storage import default_storage

def es_operador(user):
    return user.is_authenticated and user.is_staff and user.is_active

operador_required = user_passes_test(es_operador, login_url='home:login')

def guardar_archivo(upload, user):
    filename = default_storage.save(f"uploads/{upload.name}", upload)
    return Archivo.objects.create(
        nombre=upload.name,
        nombre_temporal=filename,
        ruta=filename,
        tipo=upload.content_type,
        tamano=upload.size,
        fk_user=user,
    )

# Create your views here.
def index(request):
    return render(request, 'home/index.html')

def base(request):
    return render(request, 'home/base.html')

def categoria(request):
    return render(request, 'home/categoria.html')

def contactanos(request):
    return render(request, 'home/contactanos.html')

@login_required
def crear_publicacion(request):
    return render(request, 'home/crear_publicacion.html')

@operador_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
 
        if not username or not password1:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return redirect('home:crear_usuario')
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:crear_usuario')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('home:crear_usuario')
        
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        rol = request.POST.get('rol')
        user.is_staff = rol in ['editor', 'administrador']
        user.is_superuser = rol == 'administrador'
        user.save()
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('home:crud_usuarios')
    
    return render(request, 'home/crear_usuario.html') 


@login_required
def crud_cambiar_contrasena(request):
    if request.method == 'POST':
        actual = request.POST.get('actual')
        nueva = request.POST.get('nueva')
        confirmar = request.POST.get('confirmar')

        user = request.user
        
        if not user.check_password(actual):
            messages.error(request, 'La contraseña actual es incorrecta.')
            return redirect('home:crud_cambiar_contrasena')
        
        if nueva != confirmar:
            messages.error(request, 'Las nuevas contraseñas no coinciden.')
            return redirect('home:crud_cambiar_contrasena')

        user.set_password(nueva)
        user.save()
        update_session_auth_hash(request, user)

        messages.success(request, 'Contraseña actualizada correctamente.')
        return redirect('home:crud_cambiar_contrasena')
    
    return render(request, 'home/crud_cambiar_contrasena.html')

@operador_required
def crud_categorias(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        if nombre:
            Categoria.objects.create(nombre=nombre, fk_user=request.user)
            messages.success(request, 'Categoría agregada correctamente.')
            return redirect('home:crud_categorias')
    categorias = Categoria.objects.all().order_by('-createdat')
    return render(request, 'home/crud_categorias.html', {'categorias': categorias})

@operador_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            categoria.nombre = nombre
            categoria.save()
            messages.success(request, 'Categoría actualizada correctamente.')
        return redirect('home:crud_categorias')
    return render(request, 'home/editar_categoria.html', {'categoria': categoria})

@operador_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada correctamente.')
    return redirect('home:crud_categorias')

@login_required
def crud_comentarios(request):
    return render(request, 'home/crud_comentarios.html')

@login_required
def crud_noticias(request):
    return render(request, 'home/crud_noticias.html')

@login_required
def crud_perfil(request):
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        foto = request.FILES.get('foto')

        if not username:
            messages.error(request, 'El usuario es obligatorio.')
            return redirect('home:crud_perfil')
        if User.objects.filter(username=username).exclude(pk=user.pk).exists():
            messages.error(request, 'Ese nombre de usuario ya está en uso.')
            return redirect('home:crud_perfil')

        user.username = username
        if email:
            user.email = email
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        user.save()
        
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
    
        if foto:
            if perfil.foto_perfil:
                archivo_anterior = perfil.foto_perfil
                if archivo_anterior.ruta and hasattr(archivo_anterior.ruta, 'path') and os.path.exists(archivo_anterior.ruta.path):
                    os.remove(archivo_anterior.ruta.path)
                archivo_anterior.delete()

            perfil.foto_perfil = guardar_archivo(foto, user)
        perfil.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('home:perfil')
    return render(request, 'home/crud_perfil.html', {'perfil_usuario': perfil})

@login_required
def crud_usuarios(request):
    for usuario in User.objects.all():
        Perfil.objects.get_or_create(user=usuario)
    usuarios = User.objects.select_related('perfil').order_by('date_joined')
    return render(request, 'home/crud_usuarios.html', {'usuarios': usuarios})

@login_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
 
        if not username or not password1:
            messages.error(request, 'Usuario y contraseña son obligatorios.')
            return redirect('home:crear_usuario')
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:crear_usuario')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El usuario ya existe.')
            return redirect('home:crear_usuario')
 
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        rol = request.POST.get('rol')
        user.is_staff = rol in ['editor', 'administrador']
        user.is_superuser = rol == 'administrador'
        user.save()
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('home:crud_usuarios')
    return render(request, 'home/crear_usuario.html')

def login(request):
    return render(request, 'home/login.html')
    
def noticia(request):
    return render(request, 'home/noticia.html')

@login_required
def perfil(request):
    perfil_usuario, _ = Perfil.objects.get_or_create(user=request.user)
    return render(request, 'home/perfil.html', {'perfil_usuario': perfil_usuario})

def sign_up(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        apellido_paterno = request.POST.get('apellido_paterno', '').strip()
        apellido_materno = request.POST.get('apellido_materno', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
 
        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return redirect('home:sign_up')
 
        if User.objects.filter(username=username).exists():
            messages.error(request, 'El nombre de usuario ya está en uso.')
 
            return redirect('home:sign_up')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'El correo electrónico ya está registrado.')
            return redirect('home:sign_up')
        
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.first_name = first_name
        user.last_name = ' '.join(filter(None, [apellido_paterno, apellido_materno]))
        user.save()
        perfil, _ = Perfil.objects.get_or_create(user=user)
        perfil.apellido_paterno = apellido_paterno
        perfil.apellido_materno = apellido_materno
        perfil.save()
        messages.success(request, 'Tu cuenta ha sido creada con éxito. Ahora puedes iniciar sesión.')
        return redirect('home:login')
    return render(request, 'home/sign_up.html')

@operador_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    perfil, _ = Perfil.objects.get_or_create(user=usuario)
    if request.method == 'POST':
        usuario.username = request.POST.get('username', usuario.username).strip()
        usuario.email = request.POST.get('email', usuario.email).strip()
        usuario.first_name = request.POST.get('first_name', usuario.first_name).strip()
        perfil.apellido_paterno = request.POST.get('apellido_paterno', perfil.apellido_paterno).strip()
        perfil.apellido_materno = request.POST.get('apellido_materno', perfil.apellido_materno).strip()
        usuario.last_name = ' '.join(filter(None, [perfil.apellido_paterno, perfil.apellido_materno]))
        rol = request.POST.get('rol')
        if rol:
            usuario.is_staff = rol in ['editor', 'administrador']
            usuario.is_superuser = rol == 'administrador'
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 or password2:
            if password1 != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('home:editar_usuario', pk=usuario.pk)
            usuario.set_password(password1)
        usuario.save()
        perfil.save()
        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('home:crud_usuarios')
    return render(request, 'home/crear_usuario.html', {
        'usuario_editado': usuario,
        'perfil_editado': perfil,
    })


@operador_required
def bloquear_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if usuario != request.user:
        usuario.is_active = not usuario.is_active
        usuario.save()
    return redirect('home:crud_usuarios')


@operador_required
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST' and usuario != request.user:
        usuario.delete()
    return redirect('home:crud_usuarios') 
