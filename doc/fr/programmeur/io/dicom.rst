Lecture et écriture DICOM
=========================

Lecture DICOM
-------------

Lecture de fichiers contenant une seule série
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dans le cas le plus simple, on souhaite charger un ensemble de fichiers dont on
sait qu'ils ne contiennent qu'une seule série.

::

    import medipy.io.dicom
    
    # Chargement des fichiers
    datasets = [medipy.io.dicom.read(f) for f in filenames]
    # Création de l'image
    image = medipy.io.dicom.image(datasets)

Lecture de fichiers contenant plusieurs séries
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Si on souhaite charger un ensemble de fichiers qui contiennent potentiellement
plusieurs séries, il faut d'abord diviser l'ensemble des Data Sets chargés en
séries, puis choisir l'une d'entre elles.

::

    import medipy.io.dicom
    
    datasets = [medipy.io.dicom.read(f) for f in filenames]
    # Division des DataSets en séries
    series = medipy.io.dicom.series(datasets)
    for serie in series :
        # Récupération des valeurs des attributs Series Instance UID et 
        # Series Description
        uid, description = medipy.io.dicom.uid_and_description(serie)
        print description
    image = medipy.io.dicom.image(series[0])


Lecture d'un DICOMDIR
^^^^^^^^^^^^^^^^^^^^^

Toutes les fonctions décrites précédemment acceptent aussi des Data Sets chargés
depuis des DICOMDIRs. La fonction ``load_dicomdir_records`` se charge ensuite
de charger les fichiers référencés depuis les informations du DICOMDIR. Cette
fonction accepte aussi des Data Sets, mais se contente de les retourner.

Certaines fonctions ont cependant besoin d'un argument
supplémentaire : le nom du répertoire contenant le DICOMDIR. Il s'agit de :

  * load_dicomdir_records
  * uid_and_description

::
    
    import medipy.io.dicom

    datasets = [medipy.io.dicom.read(f) for f in filenames]
    series = medipy.io.dicom.series(datasets)
    for serie in series :
        # Récupération des valeurs des attributs Series Instance UID et 
        # Series Description
        uid, description = medipy.io.dicom.uid_and_description(serie)
        print description
    # Chargement des DataSets à partir des Directory Records
    serie = medipy.io.dicom.load_dicomdir_records(series[0])
    image = medipy.io.dicom.image(serie)

Cas général
^^^^^^^^^^^

Dans le cas le plus général, chaque série peut être composée de plusieurs piles
(ensemble de coupes ayant la même orientation), par exemple dans le cas du
localisateur en IRM. La fonction ``stacks`` permet de diviser une série en piles.

::
    
    import medipy.io.dicom

    datasets = [medipy.io.dicom.read(f) for f in filenames]
    series = medipy.io.dicom.series(datasets)
    serie = medipy.io.dicom.load_dicomdir_records(series[0])
    # Division de la série en piles
    stack = medipy.io.dicom.stacks(serie)[0]
    image = medipy.io.dicom.image(stack)

Écriture DICOM
--------------

Un DataSet peut être sauvé dans un fichier en utilisant la fonction 
``medipy.io.dicom.write``. Une particularité est à prendre en compte : toutes 
les chaînes de caractères sont sauvées en UTF-8 ; l'élément Specific Character 
Set (0008,0005) est donc fixé à "ISO_IR 192".

::

    import medipy.io.dicom
    
    dataset = medipy.io.dicom.DataSet()
    # Modification du DataSet ...
    
    medipy.io.dicom.write(dataset, "foo.dcm")

Encapsulation d'un document au format DICOM
-------------------------------------------

Le standard DICOM permet de stocker tout type de document dans un Data Set [#]_.
Le module :mod:`medipy.io.dicom.encapsulated_document` permet d'encapsuler un 
fichier dans un Data Set, et d'exposer un fichier précédemment encapsulé. Les
fonctions contenues dans ce module ne génèrent pas un Data Set directement 
envoyable sur un nœud DICOM, seuls les modules DICOM concernant l'objet
Encapsulated Document sont présents. L'exemple suivant permet d'obtenir un
Data Set « correct » pour le stockage. 

.. [#] PS 3.3-2011, A.1.2.16, p. 121 et PS 3.3-2011, A.45, p. 278 