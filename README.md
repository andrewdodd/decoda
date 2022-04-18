# Decoda

This is a utility service for decoding the data from a J1939 payload. It began as a personal side project, but it should be useful if you find yourself with some J1939 frames and only the PDFs/DA from SAE to decode them! 😉

You can find this library being used with a cutdown sepc file at: https://www.decoda.cc/

## How to install it?

Like most Python libraries, you can install it via Pip:

> pip install decoda

To avoid polluting your system Python, you should probaby do this in a virtualenv, or whatever isolation mechanism you use.

## What does the install give me?

The library gives you:

1. A `spec_provider` object that will load a [`J1939Spec`](https://github.com/andrewdodd/decoda/blob/3132fc8b8ce8dfb2be298bc74e7beb9fae289523/src/decoda/spec_loader.py#L40) object (a collection of repositories) from a JSON spec file (more on this later):
   ```
   from decoda import spec_provider
   
   spec = spec_provider.provide()  # This loads from J1939_SPEC_PATH environment variable or "./decoda_spec.json"
   ```

1. A [`J1939Spec`](https://github.com/andrewdodd/decoda/blob/3132fc8b8ce8dfb2be298bc74e7beb9fae289523/src/decoda/spec_loader.py#L40) object to provide lookup access to Python objects that represent parts of the J1939 specification:
    ```
    from decoda.spec_loader import spec_provider
    
    spec = spec_provider.provide()
    
    # Lookup PGNs, SPNs etc
    pgn_0 = spec.PGNs.get_by_id(0)                     # PGN(id=0, name='Torque/Speed Control 1', ...)
    spn_695 = spec.SPNs.get_by_id(695)                 # SPN(id=695, name='Engine Override Control Mode', ...)
    manufacturer_8 = spec.Manufacturers.get_by_id(8)   # Manufacturer(id=8, name='Caterpillar Inc.', ...)
    ig_1 = spec.IndustryGroups.get_by_id(1)            # IndustryGroup(id=1, description='On-Highway Equipment', ...)
    spec.preferred_address_name(247, industry_group=1) # 'Auxiliary Power Unit (APU) #1'
    spec.preferred_address_name(247, industry_group=2) # 'Task Control (Mapping Computer)'
    ```

1. Utility functions and `PGN` objects that can take an application payload (a `bytearray`) and decode into useful objects:
   ```
   from decoda import spec_provider
    
   spec = spec_provider.provide()
    
   pgn_0 = spec.PGNs.get_by_id(0)
   
   decoded_spns = pgn_0.decode((0x123456789ABCDEF0).to_bytes(8, "big"))
   decoded_spns[0] # DecodedSPN(id=695, name='Engine Override Control Mode', value='Torque control ...)
   ...
   ```

1. Some stateful classes (found in the `decoda.transport` module) that can be used to defragment messages from a series of frames:
   ```
   from decoda import ConnectionManager, Decoda, spec_provider
   
   def my_decoded_message_handler(message):
       print(f"Do what we want with the message: {message}")
       
   def my_defrag_error_handler(reason, info):
       print(f"Handle the error if we care: {reason} - {info}")
       
   spec = spec_provider.provder()
   decoda = Decoda(spec, my_decoded_message_handler)
   cm = ConnectionManager(decoda, my_defrag_error_handler)
   
   for can_id, payload in ...some stream of received frames...:
       cm.handle_frame(can_id, payload)
   ```

1. A number of conversion scripts that can be used to create the JSON spec file from the SAE digital annex (more info later on).

## How to use it?

There is a very basic `demo.py` file that comes with this library (but it is not bundled into the decoda dependency). It shows:

 * How to load the spec into a repository
 * How to obtain spec objects from the repository
 * How to use those objects to decode payload

For example, doing these steps will probably work for you and show some example output:

```
> pip install decoda   # install the decoda lib
> curl https://raw.githubusercontent.com/andrewdodd/decoda/main/demo.py > demo.py   # download the minimal extract spec file
> curl https://raw.githubusercontent.com/andrewdodd/decoda/main/extract.json > decoda_spec.json  # download the demo.py file
> python ./demo.py
```

Beyond this, it is up to you how you use it, but it is probably some extension to what the demo examples do.


## But what if I want more than what is in the `extract.json` file?

The rights to J1939 are held by SAE (and others). I have only included a bare minimum spec file for this reason. The extract is enough to demo a number of major features of the library (variable length PGN handling, conditional behaviour of some SPNs, etc), but only includes a small fraction of the whole SAE spec.

However, if you own a copy of the SAE Digital Annex ([link](https://www.sae.org/standards/content/j1939da_202201/)), then this library provides a number of bundled [scripts](https://github.com/andrewdodd/decoda/tree/main/src/decoda/sae_spec_converter) to convert the XLS file to a suitable JSON spec file.  The code for these scripts borrows heavliy from the [pretty_j1939](https://github.com/nmfta-repo/pretty_j1939) library, but it has been adjusted to work in a slightly different way.

When I extract from a digital annex, I generally run all of these following steps (which use the console scripts exported by the Decoda libary, see [setup.py entry_points](https://github.com/andrewdodd/decoda/blob/main/setup.py#L40-L47)):

1. Extract just the raw spec data from the XLS (replacing `PATH_TO_DIGITAL_ANNEX` with the path to the XLS file):  
```
json_from_digital_annex <PATH_TO_DIGITAL_ANNEX.XLS> ./J1939DA.spec.json --pretty
```

2. Run the enrichment script (e.g. identifying enum encodings, data ranges etc)
```
enrich_spec ./J1939DA.spec.json ./J1939DA.enriched.json --pretty
```

3. Incorporate any manual corrections files you might have (e.g. I have 4-5 of these for various things, you can make these by hand or reach out if you want any tips):
```
correct_spec --corrections_path ./<CORRECTIONS FOLDER> ./J1939DA.enriched.json ./J1939DA.corrected.json --pretty
```

*NB: sometimes there are manual corrections made that need to be made to the spec file, as the digital annexes and pretty_j1939 conversion functions have bugs/mistakes.*

4. Strip things that we know definitely will not work (items with missing data etc):
```
remove_bad_items ./J1939DA.corrected.json ./J1939DA.cleaned.json --pretty
```

5. Copy the final spec file to the default name used by Decoda (alternatively you can set the path to the file via the `J1939_SPEC_FILE` environment variable):
```
cp J1939DA.cleaned.json decoda_spec.json
```


## FAQ
No one has asked these, but I'm guessing at what they might ask...

### I don't have the SAE digital annex, will this work for me?
Probably not, as it is a lot of work to create your own spec file. However, it can be done (I did it by hand until I found [pretty_j1939](https://github.com/nmfta-repo/pretty_j1939)).

### Does this library talk Controller Area Network (CAN)?
No, this library is only focussed on converting an application payload that you *know* is encoded in the SAE J1939 standard, and making it more friendly to view and work with (by performing data conversions and returning "objects").

### Are there other libraries in this space?
Yes. There seem to be quite a few in this area. Some are focussed on J1939, and some are more broadly about Controller Area Network (CAN). Some examples are:

 * [pretty_j1939](https://github.com/nmfta-repo/pretty_j1939), *"python libs and scripts for pretty-printing J1939 logs"*
   - This library is the one that inspired me to attempt to build the spec files out of the SAE digital annex files. The authors of this library also seem to be much more involved in vehicle networks, CAN and J1939 than I ever have been. The code in this library seems to know much more about the domain of using J1939.
   - I had already worked on the decoding part well before I saw this library, so I have not adopted their decoding technique, but overall this seems like a good library.

 * [python-j1939](https://github.com/milhead2/python-j1939), *"Breakout of j1939 from inside the python-can package"*
   - This library seems focussed on the J1939 framing and encoding details, and is not so focussed on decoding the application layer data. I think is it used to "talk J1939" by using the `python-can` project to "talk CAN".

 * [python-can](https://github.com/hardbyte/python-can), *"The can package provides controller area network support for Python developers"*
   - This libary provides "talk CAN" functiionality in Python language bindings. I.e. you would use this to "talk CAN" to a CANBus.

 * [canmatrix](https://github.com/ebroecker/canmatrix), *"Converting Can (Controller Area Network) Database Formats .arxml .dbc .dbf .kcd ..."*
   - The CAN world has its own set of database formats (which I know nothing about, and find kind of arcane). As far as I can tell, this library can read and convert them.

### Is Decoda any good?
I think so, but hey, I wrote it. I think it does some things well, such as:

 - Using a human and machine readable spec (JSON) to decode application layer payloads into a friendly, human and machine readable form (Python objects, that serialise to JSON).
 - Coping with a lot of weirdness and complexity in J1939, for example:
   - The `demo.py` file shows decoding PGN 65226, which involves repeatable sections; complex bit locations and recursive name lookup for SPN 1214; and encoded values.
   - The `demo.py` file shows the use of SPN 2556 to control how the other SPNs in PGN 60416 should be interpreted.
 - Defining a machine and human readable specification structure for the J1939 application data (i.e. the JSON spec format).
 - Providing tools/scripts to bootstrap from the SAE (and isobus) digital annex to get a workable spec file.

## Extra stuff

### What is the isobus converter for?
I use this to create a "corrections" file for just the stuff available from the ISOBUS "SPNs and PGNs" XLSX file found here: https://www.isobus.net/isobus/

For example, I do this:
```
> # Download the relevant XLSX file from https://www.isobus.net/isobus/, however you like
> mkdir ./corrections       # make a place for the corrections to go
> json_from_isobus_xlsx --pretty "SPNs and PGNs.xlsx" ./corrections/iso-11783.json
```

Then when I run the `correct_spec` script (step 3 above), the corrections from this file will be applied.

### How can I supply the spec from a different location?
By default the library looks for a file called `decoda_spec.json` in the execution path. If you want to supply a different file, you can set the `J1939_SPEC_FILE` environment variable.

The relevant code is [here](https://github.com/andrewdodd/decoda/blob/main/src/decoda/spec_loader.py#L256).
