from models import Contact


def preparar_correo(contacto: Contact) -> dict:
    return {
        "to": contacto.email,
        "subject": "Mensaje Importante",
        "body": f"Hola {contacto.nombre}, este es un mensaje importante.",
    }
