<StyledLayerDescriptor xmlns="http://www.opengis.net/sld" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:se="http://www.opengis.net/se" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ogc="http://www.opengis.net/ogc" xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.1.0/StyledLayerDescriptor.xsd" version="1.1.0">
  <NamedLayer>
    <se:Name>EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1</se:Name>
    <UserStyle>
      <se:Name>EMSR685_AOI01_GRA_PRODUCT_observedEventA_v1</se:Name>
      <se:FeatureTypeStyle>

        <se:Rule>
          <se:Name>Burnt area (grading)</se:Name>
          <se:Description>
            <se:Title>Burnt area</se:Title>
          </se:Description>
          <ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
		  <ogc:PropertyIsEqualTo>
			<ogc:PropertyName>notation</ogc:PropertyName>
			<ogc:Literal>Burnt area</ogc:Literal>
		  </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <se:LineSymbolizer>
            <se:Stroke>
              <se:SvgParameter name="stroke">#ffaa00</se:SvgParameter>
              <se:SvgParameter name="stroke-width">3</se:SvgParameter>
              <se:SvgParameter name="stroke-linejoin">bevel</se:SvgParameter>
              <se:SvgParameter name="stroke-linecap">square</se:SvgParameter>
            </se:Stroke>
          </se:LineSymbolizer>
        </se:Rule>

        </se:FeatureTypeStyle>







    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
