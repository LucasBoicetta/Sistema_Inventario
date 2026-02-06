from app import db
from flask import render_template, redirect, url_for, flash, request , make_response
from flask_jwt_extended import current_user
from app.shared.models import User
from .forms import LoginForm
from .services import AuthService, AuthenticationError
from . import auth_bp
import sqlalchemy as sa
from flask_jwt_extended import (set_access_cookies, set_refresh_cookies, unset_jwt_cookies,
                                jwt_required, get_jwt_identity, verify_jwt_in_request)
from app.shared.decorators import jwt_required_html

# ----- RUTAS DE AUTENTICACIÓN -----


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    #1. Verificar si ya está logueado.
    try:
        #Verifica si hay token válido en las cookies.
        verify_jwt_in_request(optional=True)
        if get_jwt_identity():
            return redirect(url_for('main.index'))
    
    except Exception:
        #Si el token es inválido o expiró, lo ignoramos y mostramos el login.
        pass

    #2. Procesar formulario.

    form = LoginForm()

    if form.validate_on_submit():
        try:
            #Llamamos al servicio.
            result = AuthService.authenticate_user(
                cedula=form.cedula.data,
                password=form.password.data
            )

            #Preparamos la respuesta (Manejo HTTP/Cookies).
            resp = make_response(redirect(url_for('main.index')))

            #Guardar JWTs en Cookies HTTPOnly(Seguro)
            set_access_cookies(resp, result['access_token'])
            set_refresh_cookies(resp, result['refresh_token'])

            flash(f'Se ha iniciado sesión como {result["user"].nombre}', 'success')
            return resp
        except AuthenticationError as e:
            flash(str(e), 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/cambiar_contraseña', methods=['GET', 'POST'])
@jwt_required_html()
def cambiar_contraseña():
    if request.method=='POST':
        try:
            AuthService.change_password(
                user=current_user,
                current_password=request.form.get('current_password'),
                new_password=request.form.get('new_password'),
                confirm_password=request.form.get('confirm_password')
            )
            flash('Contraseña cambiada exitosamente.', 'success')
            return redirect(url_for('main.index'))
        
        except AuthenticationError as e:
            flash(str(e), 'danger')
            #No redirigimos, para que el usuario pueda intentar de nuevo.

    return render_template('auth/cambiar_contraseña.html')


@auth_bp.route('/logout')
@jwt_required_html()
def logout():
    resp = make_response(redirect(url_for('auth.login')))
    #Flask-JWT elimina las cookies por nosotros.
    unset_jwt_cookies(resp)
    flash('Se ha cerrado la sesión correctamente.', 'success')
    return resp

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True) #Solo accesible con refresh token.
def refresh():
    """Endpoint para renovar el token de acceso transparentemente."""
    current_user_id = get_jwt_identity()
    new_token = AuthService.refresh_access(current_user_id)

    resp = make_response(redirect(request.referrer or url_for('main.index')))
    set_access_cookies(resp, new_token)
    return resp